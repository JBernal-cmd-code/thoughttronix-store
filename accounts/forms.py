from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import Address, User


class SignupForm(UserCreationForm):
    """Django's stock signup fields plus email — username, email, password
    and confirmation.

    Signing up still asks for the minimum, and email is now part of that
    minimum: without one, a customer who forgets their password has no way
    back in. The model lowercases the address and refuses one that's
    already registered, in any capitalization. The widgets carry DaisyUI
    classes because plain Django forms own their own styling here.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
        help_texts = {"email": "Used only to help you get back into your account."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    @property
    def email_taken(self):
        """True when the email was refused as already registered — the
        template then offers the forgot-password link beside the error."""
        return self.has_error("email", "unique")


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class PasswordResetRequestForm(PasswordResetForm):
    """Django's reset request, limited to customers.

    Django already skips inactive users and users without a usable
    password; this also skips staff, so someone who gets into an
    employee's inbox can't take over the back office. Staff recovery goes
    through the admin. Whoever matches, the view shows the same page, so
    nothing reveals which emails are registered or which belong to staff.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["class"] = "input w-full"

    def get_users(self, email):
        # Emails are stored lowercase, so the input is lowercased to match.
        return (user for user in super().get_users(email.lower()) if not user.is_staff)


class SetNewPasswordForm(SetPasswordForm):
    """The new password, twice, checked by the project's validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class AddressForm(forms.ModelForm):
    """An entry in the customer's address book.

    Every rule comes from the model: ``state`` renders as a select from
    its ``choices``, ``zip_code`` carries the shared ZIP validator, and
    ``line2`` is the one optional field. ``user`` is never a form field —
    the view attaches it from ``request.user``.
    """

    class Meta:
        model = Address
        fields = ["full_name", "street", "line2", "city", "state", "zip_code"]
        labels = {
            "full_name": "Full name",
            "street": "Street address",
            "line2": "Apt, suite, etc. (optional)",
            "city": "City",
            "state": "State",
            "zip_code": "ZIP code",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            else:
                widget.attrs["class"] = "input w-full"
