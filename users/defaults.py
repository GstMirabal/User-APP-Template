"""App-level defaults for the settings this app consumes.

A reusable app must work when dropped into a project that has never heard of
it. These accessors read the host's settings when present and fall back to a
sane value otherwise, so a consumer only declares what it wants to change.

Values that are NOT defaulted, because guessing them would be unsafe:
`AUTH_USER_MODEL`, `MASTER_KEY` and `ENCRYPTION_PEPPER`. Those must come from
the host — see `docs/contracts/USERS_CONTRACT.md`, "Host requirements".
"""

from django.conf import settings

#: Seconds a re-authentication stays valid for step-up gated endpoints.
STEP_UP_WINDOW_SECONDS_DEFAULT = 300

#: Minutes a registration verification code stays valid.
VERIFICATION_OTP_TTL_MINUTES_DEFAULT = 15


def step_up_window_seconds() -> int:
    """Return the configured step-up window, in seconds.

    Returns:
        int: `settings.STEP_UP_WINDOW_SECONDS` when the host defines it,
            otherwise `STEP_UP_WINDOW_SECONDS_DEFAULT`.
    """
    return int(
        getattr(
            settings, "STEP_UP_WINDOW_SECONDS", STEP_UP_WINDOW_SECONDS_DEFAULT
        )
    )


def verification_otp_ttl_minutes() -> int:
    """Return the configured verification-code lifetime, in minutes.

    Returns:
        int: `settings.VERIFICATION_OTP_TTL_MINUTES` when the host defines it,
            otherwise `VERIFICATION_OTP_TTL_MINUTES_DEFAULT`.
    """
    return int(
        getattr(
            settings,
            "VERIFICATION_OTP_TTL_MINUTES",
            VERIFICATION_OTP_TTL_MINUTES_DEFAULT,
        )
    )
