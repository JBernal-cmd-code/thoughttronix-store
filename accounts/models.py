from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from .constants import US_STATES, zip_validator
from .user_agents import describe_user_agent

SECURITY_EVENT_RETENTION = timedelta(days=90)


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.

    Email is required and unique, and stored lowercase, so a plain unique
    constraint is enough to keep ``Casey@Example.com`` and
    ``casey@example.com`` from becoming two accounts. Usernames remain the
    sign-in identifier.
    """

    email = models.EmailField(
        "email address",
        unique=True,
        error_messages={"unique": "That email address is already in use."},
    )
    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001

    def clean(self):
        # ModelForm validation calls clean() before validate_unique(), so
        # lowercasing here makes every form's uniqueness check
        # case-insensitive too.
        super().clean()
        self.email = self.email.lower()

    def send_password_changed_notice(self):
        """Email this user that their password changed, so a change they
        didn't make doesn't go unnoticed."""
        self.email_user(
            "Your ThoughtTronix password was changed",
            render_to_string("accounts/emails/password_changed.txt", {"user": self}),
        )

    def send_email_changed_notice(self, old_email):
        """Email the *old* address that the account email changed.

        The new address is the one that may not be theirs, so the notice
        goes where the real owner will still read it.
        """
        send_mail(
            "Your ThoughtTronix email address was changed",
            render_to_string(
                "accounts/emails/email_changed.txt",
                {"user": self, "old_email": old_email},
            ),
            None,
            [old_email],
        )


class SecurityEventQuerySet(models.QuerySet):
    def record(self, user, event_type, request):
        """Record ``event_type`` for ``user``, then prune their old events.

        The IP is the request's remote address — behind a reverse proxy
        that's the proxy, not the client. Pruning here, on every write,
        keeps each user's log to the retention window with no scheduled
        job; other users' events are left alone.
        """
        meta = request.META if request is not None else {}
        event = self.create(
            user=user,
            event_type=event_type,
            ip_address=meta.get("REMOTE_ADDR") or None,
            user_agent=meta.get("HTTP_USER_AGENT", ""),
        )
        self.filter(
            user=user, created_at__lt=timezone.now() - SECURITY_EVENT_RETENTION
        ).delete()
        return event


class SecurityEvent(models.Model):
    """Something that happened to how an account is protected.

    Shown to the account owner on the Security Center so they can spot
    activity that wasn't theirs. Sign-outs and reset requests are left out
    on purpose: neither tells the owner anything about who got in.
    """

    class EventType(models.TextChoices):
        SIGNED_IN = "signed_in", "Signed in"
        SIGN_IN_FAILED = "sign_in_failed", "Failed sign-in"
        PASSWORD_CHANGED = "password_changed", "Password changed"
        PASSWORD_RESET = "password_reset", "Password reset"
        EMAIL_CHANGED = "email_changed", "Email changed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_events",
    )
    event_type = models.CharField(max_length=20, choices=EventType)
    # A default rather than auto_now_add, so seeded history can be backdated.
    created_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    objects = SecurityEventQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.user} at {self.created_at}"

    @property
    def device(self):
        """The User-Agent as a short label, such as "Firefox on Windows"."""
        return describe_user_agent(self.user_agent)


class AddressQuerySet(models.QuerySet):
    def create_from_checkout(self, user, checkout_data):
        """Save a checkout's *shipping* values as a reusable address.

        ``checkout_data`` is the ``cleaned_data`` of a valid
        ``CheckoutForm``. Only the shipping block is saved: billing is
        prefilled from the same address, so saving both would usually
        create twins.
        """
        return self.create(
            user=user,
            full_name=checkout_data["shipping_name"],
            street=checkout_data["shipping_street"],
            line2=checkout_data["shipping_line2"],
            city=checkout_data["shipping_city"],
            state=checkout_data["shipping_state"],
            zip_code=checkout_data["shipping_zip"],
        )


class Address(models.Model):
    """A postal address saved to a customer's account.

    Untyped on purpose: an address is a place, not a role. Shipping
    versus billing is a fact about a *checkout*, not about the address,
    so one saved record can fill either section of the checkout form —
    or both.

    Not a source of truth for any placed order: ``Order`` keeps flat
    copies of the address it shipped to, so editing or deleting one of
    these can never change order history.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    full_name = models.CharField(max_length=100)
    street = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, choices=US_STATES)
    zip_code = models.CharField(max_length=10, validators=[zip_validator])

    objects = AddressQuerySet.as_manager()

    class Meta:
        ordering = ["-id"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"

    def as_checkout_initial(self):
        """This address as ``CheckoutForm`` initial data, for both sections.

        The keys are spelled out rather than built from a prefix: the
        form calls it ``shipping_zip`` while the model calls it
        ``zip_code``, so a generated mapping would silently skip it.
        """
        values = {
            "name": self.full_name,
            "street": self.street,
            "line2": self.line2,
            "city": self.city,
            "state": self.state,
            "zip": self.zip_code,
        }
        return {
            f"{section}_{suffix}": value
            for section in ("shipping", "billing")
            for suffix, value in values.items()
        }
