from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
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


class ChangePasswordForm(PasswordChangeForm):
    """The current password, then the new one twice, checked by the
    project's validators — so someone at an unlocked computer can't
    change it."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class ChangeEmailForm(forms.Form):
    """A new email, twice, and the current password.

    The address is compared and saved lowercase. It must differ from the
    current one and not belong to another account — refused with signup's
    own "already in use" wording. The change takes effect on save, with no
    confirmation link; the old address gets a notice instead.
    """

    new_email1 = forms.EmailField(label="New email address")
    new_email2 = forms.EmailField(label="New email address again")
    password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_new_email1(self):
        email = self.cleaned_data["new_email1"].lower()
        if email == self.user.email:
            raise forms.ValidationError(
                "That's already your email address.", code="unchanged"
            )
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                User._meta.get_field("email").error_messages["unique"],
                code="unique",
            )
        return email

    def clean_new_email2(self):
        email1 = self.cleaned_data.get("new_email1")
        email2 = self.cleaned_data["new_email2"].lower()
        if email1 and email1 != email2:
            raise forms.ValidationError(
                "The two email addresses didn't match.", code="email_mismatch"
            )
        return email2

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(
                "Your password was entered incorrectly. Please enter it again.",
                code="password_incorrect",
            )
        return password

    def save(self):
        """Switch the account to the new email and notify the old one."""
        old_email = self.user.email
        self.user.email = self.cleaned_data["new_email1"]
        self.user.save(update_fields=["email"])
        self.user.send_email_changed_notice(old_email)
        return self.user


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
