"""Access-control mixins.

Per the PRD, back-office views gate on ``is_staff`` via mixins — roles
are Django's own vocabulary, nothing else. HTMX endpoints that need
sign-in use ``HtmxLoginRequiredMixin``.
"""

from urllib.parse import urlsplit, urlunsplit

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse


class StaffRequiredMixin(UserPassesTestMixin):
    """Allow staff only: anonymous users are redirected to the login
    page; signed-in non-staff get 403 (``AccessMixin``'s default split)."""

    def test_func(self):
        return self.request.user.is_staff


class HtmxLoginRequiredMixin(LoginRequiredMixin):
    """Sign-in required, for views HTMX calls.

    A plain 302 would be followed inside the HTMX request and the login page
    swapped into the target. So a signed-out HTMX request gets an
    ``HX-Redirect`` that navigates the whole browser to login, with ``next``
    set to the page the request came from (path and query only, from
    ``HX-Current-URL``). Other requests get ``LoginRequiredMixin``'s redirect.
    """

    def handle_no_permission(self):
        request = self.request
        if request.user.is_authenticated or not request.headers.get("HX-Request"):
            return super().handle_no_permission()
        current = urlsplit(request.headers.get("HX-Current-URL", ""))
        page = urlunsplit(("", "", current.path, current.query, ""))
        login = redirect_to_login(page or request.get_full_path(), self.get_login_url())
        response = HttpResponse()
        response["HX-Redirect"] = login.url
        return response
