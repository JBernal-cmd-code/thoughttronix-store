from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    AddressForm,
    ChangeEmailForm,
    ChangePasswordForm,
    PasswordResetRequestForm,
    SetNewPasswordForm,
    SignInForm,
    SignupForm,
)
from .models import Address


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account, then hand off to the login page.

    New users sign in themselves — auto-login after signup is left as a
    student exercise.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Account created — you can now sign in."


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = SignInForm


class SignOutView(LogoutView):
    def post(self, request, *args, **kwargs):
        # Flash after super() has flushed the session, or the message
        # would be wiped along with it.
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out.")
        return response


# --- Forgot password ----------------------------------------------------------
#
# Django's reset views, pointed at this project's templates. The request
# form only matches customers (see PasswordResetRequestForm), and every
# visitor gets the same done page either way.

RESET_EMAIL_SESSION_KEY = "password_reset_email"


class PasswordResetRequestView(PasswordResetView):
    form_class = PasswordResetRequestForm
    template_name = "accounts/password_reset_form.html"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    email_template_name = "accounts/emails/password_reset.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    def form_valid(self, form):
        # The typed address travels to the done page in the session, never
        # the URL, so it stays out of browser history and server logs.
        self.request.session[RESET_EMAIL_SESSION_KEY] = form.cleaned_data["email"]
        return super().form_valid(form)


class PasswordResetRequestDoneView(PasswordResetDoneView):
    """The same page whether or not the email matched an account."""

    template_name = "accounts/password_reset_done.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email"] = self.request.session.get(RESET_EMAIL_SESSION_KEY)
        return context


class PasswordResetSetView(PasswordResetConfirmView):
    """Set a new password from a reset link, then sign in by hand.

    The user isn't signed in automatically: they go to the sign-in page and
    prove the new password works. Every session from before the reset is
    already dead, since the session auth hash covers the password.
    """

    form_class = SetNewPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        form.user.send_password_changed_notice()
        messages.success(
            self.request, "Your password has been reset. Sign in with your new one."
        )
        return response


# --- Security Center ----------------------------------------------------------
#
# How the signed-in user's account is protected. For every signed-in user,
# staff included, and always about request.user — no URL here takes an id.


class SecurityCenterView(LoginRequiredMixin, TemplateView):
    """The hub: username, email, links to change them, and recent activity."""

    template_name = "accounts/security.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["events"] = self.request.user.security_events.all()[:10]
        return context


class ChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    """Change the password by confirming the current one.

    Django's view keeps this session signed in (it updates the session auth
    hash); every other session dies, since the hash covers the password.
    """

    form_class = ChangePasswordForm
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("accounts:security")

    def form_valid(self, form):
        response = super().form_valid(form)
        form.user.send_password_changed_notice()
        messages.success(self.request, "Your password has been changed.")
        return response


class ChangeEmailView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    """Move the account to a new email by confirming the password.

    The form does the checking, saving, and notifying the old address.
    """

    form_class = ChangeEmailForm
    template_name = "accounts/email_change_form.html"
    success_url = reverse_lazy("accounts:security")
    success_message = "Your email address has been changed."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


# --- The address book -------------------------------------------------------
#
# A customer's saved addresses, reused at checkout. Addresses are always
# fetched through the owner — never by bare pk — so another customer's
# address is a 404, not a 403.


class OwnAddressesMixin(LoginRequiredMixin):
    """Addresses are always fetched through the owner — never by bare pk."""

    model = Address
    success_url = reverse_lazy("accounts:addresses")

    def get_queryset(self):
        return self.request.user.addresses.all()


class AddressListView(OwnAddressesMixin, ListView):
    """The customer's saved addresses, newest first per the model ordering."""

    template_name = "accounts/address_list.html"
    context_object_name = "addresses"


class AddressCreateView(OwnAddressesMixin, SuccessMessageMixin, CreateView):
    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_message = "Address saved."

    def form_valid(self, form):
        # The owner comes from the session, never from the POST.
        form.instance.user = self.request.user
        return super().form_valid(form)


class AddressUpdateView(OwnAddressesMixin, SuccessMessageMixin, UpdateView):
    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_message = "Address updated."


class AddressDeleteView(OwnAddressesMixin, SuccessMessageMixin, DeleteView):
    """A hard delete: placed orders keep their own flat copies, so no
    order history can change when an address goes away."""

    context_object_name = "address"
    template_name = "accounts/address_confirm_delete.html"
    success_message = "Address deleted."
