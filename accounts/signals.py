"""Security events recorded from Django's auth signals.

Connected in ``AccountsConfig.ready()``.
"""

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from .models import SecurityEvent, User


@receiver(user_logged_in)
def record_sign_in(sender, request, user, **kwargs):
    SecurityEvent.objects.record(user, SecurityEvent.EventType.SIGNED_IN, request)


@receiver(user_login_failed)
def record_failed_sign_in(sender, credentials, request=None, **kwargs):
    """Record a failed sign-in against the account whose username was typed.

    The signal carries only the typed credentials, so an attempt on a
    username that doesn't exist has no account to belong to and is dropped.
    """
    username = credentials.get("username")
    user = User.objects.filter(username=username).first() if username else None
    if user is not None:
        SecurityEvent.objects.record(
            user, SecurityEvent.EventType.SIGN_IN_FAILED, request
        )
