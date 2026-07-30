"""Secrets, DEBUG resolution, host/CORS allow-lists and hardening.

Part of the settings package. See `config/settings/__init__.py` for the load
order and why the split exists.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

# SECTION 2: CORE SECURITY SETTINGS
# ==============================================================================

# --- 2.1 SECRET KEY (SECRET_KEY) ---
# Ensures the application fails immediately if the SECRET_KEY is not configured.
# Documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#secret-key
# ------------------------------------------------------------------------------
try:
    SECRET_KEY = config["django_settings"]["DJANGO_SECRET_KEY"]
    if not SECRET_KEY:
        raise ValueError("DJANGO_SECRET_KEY must not be empty.")
except (KeyError, ValueError) as e:
    raise ImproperlyConfigured(
        "CRITICAL: The DJANGO_SECRET_KEY is missing or empty in your "
        f"config.toml / .env file. Error: {e}"
    ) from e


# --- 2.2 DEBUG MODE (DEBUG) ---
# SECURITY WARNING: Never run with debug turned on in production!
# Documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#debug
# ------------------------------------------------------------------------------
_TRUE_VALUES = frozenset({"true", "1", "yes", "on"})
_FALSE_VALUES = frozenset({"false", "0", "no", "off", ""})


def _as_bool(raw: object, name: str) -> bool:
    """Coerces a configuration value into a real boolean.

    `config.toml` templates its values as strings (`DEBUG = "$DEBUG"`), and
    every non-empty string is truthy in Python — so an unconverted `"False"`
    would silently keep debug mode on and skip the production hardening block
    below.

    Args:
        raw (object): The value as read from `config.toml` or the environment.
        name (str): Setting name, used in the error message.

    Returns:
        bool: The parsed value.

    Raises:
        ImproperlyConfigured: If the value is neither a boolean nor a
            recognised truthy/falsy spelling.
    """
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    text = str(raw).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    raise ImproperlyConfigured(
        f"CRITICAL: {name} must be a boolean. Got {raw!r}. "
        f"Accepted: {sorted(_TRUE_VALUES)} or {sorted(_FALSE_VALUES - {''})}."
    )


DEBUG = _as_bool(config["django_settings"].get("DEBUG"), "DEBUG")


# --- 2.3 ALLOWED HOSTS (ALLOWED_HOSTS) ---
# A critical security measure to prevent HTTP Host Header attacks.
# Documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#allowed-hosts
# ------------------------------------------------------------------------------
if DEBUG:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
else:
    try:
        allowed_hosts_str = config["django_settings"].get("ALLOWED_HOSTS")
    except KeyError:
        allowed_hosts_str = None

    ALLOWED_HOSTS = (
        [host.strip() for host in allowed_hosts_str.split(",") if host.strip()]
        if allowed_hosts_str
        else []
    )

if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "CRITICAL: Running in PRODUCTION mode (DEBUG=False) but "
        "`ALLOWED_HOSTS` is empty. Define it in the "
        "`[django_settings]` section of `config.toml`."
    ) from None


# --- 2.4 ALLOWED ORIGINS FOR CORS (CORS_ALLOWED_ORIGINS) ---
# Controls which frontend domains can access this API.
# Documentation (django-cors-headers): https://github.com/adamchainz/django-cors-headers
# ------------------------------------------------------------------------------
if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4200",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4200",
    ]
else:
    try:
        cors_origins_str = config["django_settings"].get("CORS_ALLOWED_ORIGINS")
    except KeyError:
        cors_origins_str = None

    CORS_ALLOWED_ORIGINS = (
        [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
        if cors_origins_str
        else []
    )

if not DEBUG and not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CRITICAL: Running in PRODUCTION mode (DEBUG=False) but "
        "`CORS_ALLOWED_ORIGINS` is empty. Define it in the "
        "`[django_settings]` section of `config.toml`."
    ) from None


# --- 2.5 ENCRYPTION CONFIGURATION (MASTER_KEY, ENCRYPTION_PEPPER) ---
# Keys for application-level encryption and blind indexing.
# ------------------------------------------------------------------------------
try:
    security_config = config.get("security", {})
    MASTER_KEY = security_config.get("MASTER_KEY")
    ENCRYPTION_PEPPER = security_config.get("ENCRYPTION_PEPPER")

    if not MASTER_KEY or not ENCRYPTION_PEPPER:
        # Fallback to environment variables if not in config.toml (for flexibility)
        MASTER_KEY = MASTER_KEY or os.environ.get("MASTER_KEY")
        ENCRYPTION_PEPPER = ENCRYPTION_PEPPER or os.environ.get("ENCRYPTION_PEPPER")

    if not MASTER_KEY:
        raise ValueError("MASTER_KEY must be set for encryption.")
    if not ENCRYPTION_PEPPER:
        raise ValueError("ENCRYPTION_PEPPER must be set for blind indexing.")

except (KeyError, ValueError) as e:
    # In production, this should be a hard failure.
    if not DEBUG:
        raise ImproperlyConfigured(
            f"CRITICAL: Encryption configuration failed. {e}"
        ) from e
    else:
        # In DEBUG, we can warn or set dummy values if strictly necessary,
        # but better to fail early to ensure dev/prod parity.
        print(f"WARNING: Encryption keys missing in DEBUG mode. {e}")
        # Deliberately fails here too, rather than substituting development
        # defaults: dev/prod parity on the encryption path is worth more than
        # the convenience of booting without keys.
        raise ImproperlyConfigured(f"Encryption keys missing. {e}") from e


# ==============================================================================
# SECTION 3: PRODUCTION-ONLY SECURITY ENHANCEMENTS
# ==============================================================================
# Hardens the application when `DEBUG` is False by configuring security headers.
# Documentation: https://docs.djangoproject.com/en/5.2/topics/security/#security-middleware
# ------------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    CSP_DEFAULT_SRC = ("'self'",)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "no-referrer"
    SECURE_PERMISSIONS_POLICY = {
        "geolocation": "()",
        "microphone": "()",
        "camera": "()",
        "fullscreen": "()",
        "payment": "()",
    }


# ==============================================================================
# SECTION 7: PASSWORD VALIDATION AND HASHING
# ==============================================================================

# -- 7.1: Password Validators --
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.core.validators.PasswordComplexityValidator"},
    # Rejects passwords known to appear in public breach corpora. Queries the
    # Have I Been Pwned range API with a k-anonymity prefix, so the password
    # itself never leaves this process. Fails open if the API is unreachable:
    # an outage must not block registration. Stripped in settings_test to keep
    # the suite hermetic.
    {"NAME": "pwned_passwords_django.validators.PwnedPasswordsValidator"},
]

# -- 7.2: Password Hashers --
# https://docs.djangoproject.com/en/5.2/topics/auth/passwords/#password-storage
# ------------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# -- 7.3: Cookie and Session Security --
# ------------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"


# ==============================================================================
