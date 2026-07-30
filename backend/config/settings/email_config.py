"""Email backend, strict in production and console-only in DEBUG.

Part of the settings package. See `config/settings/__init__.py` for the load
order and why the split exists.
"""

from django.core.exceptions import ImproperlyConfigured

from .cache import *

# SECTION 9: EMAIL CONFIGURATION
# ==============================================================================
# Dynamically configures the email backend based on the DEBUG flag.
# Docs: https://docs.djangoproject.com/en/5.2/topics/email/
# ------------------------------------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    try:
        email_config = config["email_settings"]
        EMAIL_HOST = email_config["EMAIL_HOST"]
        EMAIL_PORT = email_config["EMAIL_PORT"]
        EMAIL_USE_TLS = email_config["EMAIL_USE_TLS"]
        EMAIL_HOST_USER = email_config["EMAIL_HOST_USER"]
        EMAIL_HOST_PASSWORD = email_config["EMAIL_HOST_PASSWORD"]

        if not all([EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD]):
            raise ValueError(
                "EMAIL_HOST, EMAIL_HOST_USER and EMAIL_HOST_PASSWORD "
                "must not be empty in production."
            )
    except (KeyError, ValueError) as e:
        raise ImproperlyConfigured(
            "CRITICAL: Production email configuration failed. Check the "
            f"[email_settings] section in config.toml and .env. Original error: {e}"
        ) from e


# ==============================================================================
