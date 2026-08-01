"""System checks for host configuration this app cannot supply itself.

Each one covers a setting whose absence produces no exception, only silently
degraded behaviour. That is precisely the class of defect a system check is
for: it fails at `manage.py check`, which CI runs, rather than in production
where the symptom is something not happening.
"""

from typing import Any

from django.conf import settings
from django.core.checks import CheckMessage, register
from django.core.checks import Warning as DjangoWarning

from .events import verification_code_issued


@register()
def check_verification_delivery_is_wired(
    app_configs: Any, **kwargs: Any
) -> list[CheckMessage]:
    """Warn when nothing listens for `verification_code_issued`.

    The app announces the code and does not deliver it, so with no receiver
    connected, registration completes and the account can never be verified —
    the plaintext exists only inside that signal, and the stored column is
    encrypted and never read back.

    Nothing raises in that state, which is why it is worth a check.

    Args:
        app_configs: Unused; the check is not per-app.
        **kwargs: Additional arguments passed by Django's check framework.

    Returns:
        list[CheckMessage]: A single `users.W001` when no receiver is
            connected, an empty list otherwise.
    """
    if verification_code_issued.has_listeners():
        return []
    return [
        DjangoWarning(
            "Nothing is connected to the `verification_code_issued` signal, so "
            "verification codes are issued and never delivered.",
            hint=(
                "Connect a receiver in your project and send the code however "
                "you reach users:\n\n"
                "    from django.dispatch import receiver\n"
                "    from users.events import verification_code_issued\n\n"
                "    @receiver(verification_code_issued)\n"
                "    def deliver(sender, user, code, expires_at, **kwargs):\n"
                "        send_mail(..., recipient_list=[user.email])\n\n"
                "See docs/contracts/USERS_CONTRACT.md, 'Host requirements'."
            ),
            id="users.W001",
        )
    ]


@register()
def check_axes_username_field_is_pinned(
    app_configs: Any, **kwargs: Any
) -> list[CheckMessage]:
    """Warn when `django-axes` will record failed logins against nobody.

    From axes 8 the default for `AXES_USERNAME_FORM_FIELD` is derived from the
    user model's `USERNAME_FIELD`, which is `email` here, while Django's own
    `AuthenticationForm` names its field `username` whatever the model says.
    Left at the default, axes stores every failed admin or `LoginView` attempt
    with `username=None`: lockout degrades from per-account to per-IP and
    `AXES_RESET_ON_SUCCESS` stops matching. Nothing raises.

    Args:
        app_configs: Unused; the check is not per-app.
        **kwargs: Additional arguments passed by Django's check framework.

    Returns:
        list[CheckMessage]: A single `users.W002` when the setting is not
            pinned to the literal form field name, an empty list otherwise.
    """
    if "axes" not in settings.INSTALLED_APPS:
        return []
    # The library's lazy default proxies both `==` and `isinstance`, so only
    # the concrete type tells a pinned value apart from a derived one.
    value = getattr(settings, "AXES_USERNAME_FORM_FIELD", None)
    if type(value) is str and value == "username":
        return []
    return [
        DjangoWarning(
            "AXES_USERNAME_FORM_FIELD is not pinned, so django-axes will "
            "record failed logins with username=None and brute-force "
            "protection degrades from per-account to per-IP.",
            hint=(
                'Set AXES_USERNAME_FORM_FIELD = "username" in your settings. '
                "See docs/contracts/USERS_CONTRACT.md, 'Host requirements'."
            ),
            id="users.W002",
        )
    ]
