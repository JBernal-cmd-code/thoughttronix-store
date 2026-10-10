"""Security events recorded from Django's auth signals.

Connected in ``AccountsConfig.ready()``.
"""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import SecurityEvent


@receiver(user_logged_in)
def record_sign_in(sender, request, user, **kwargs):
    SecurityEvent.objects.record(user, SecurityEvent.EventType.SIGNED_IN, request)
