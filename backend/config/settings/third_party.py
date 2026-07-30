"""Django REST Framework, SimpleJWT, django-axes and drf-spectacular.

Part of the settings package. See `config/settings/__init__.py` for the load
order and why the split exists.
"""

import datetime
import logging
import os

from .email_config import *

# SECTION 11: DJANGO REST FRAMEWORK & JWT CONFIGURATION
# ==============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
        "sensitive": "5/minute",  # Para login/register
    },
}


# ==============================================================================
# SECTION 12: THIRD PARTY CONFIGURATIONS (AXES, SPECTACULAR)
# ==============================================================================

# -- 12.1: Authentication Backends (Axes) --
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# -- 12.2: Axes Settings (Brute Force Protection) --
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = datetime.timedelta(minutes=15)
AXES_LOCKOUT_TEMPLATE = None  # Returns JSON through DRF
AXES_RESET_ON_SUCCESS = True
# Lock on the (username, IP) pair. A nested list means "combine these", which
# is the Axes 6 replacement for the removed
# AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP boolean.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]

# -- 12.3: Spectacular Settings (OpenAPI) --
SPECTACULAR_SETTINGS = {
    "TITLE": "User-APP-Template API",
    "DESCRIPTION": "Security-first Identity and Authentication Template.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_PATCH": True,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Signing key separated from SECRET_KEY (ADR-0003). Sharing them made any
# disclosure of the session-signing secret an immediate token-forgery
# capability, and forced both to rotate together. Falls back with a warning
# rather than failing to boot, so an existing deployment is not locked out by
# the upgrade.
JWT_SIGNING_KEY = (
    config.get("security", {}).get("JWT_SIGNING_KEY")
    or os.environ.get("JWT_SIGNING_KEY")
)
if not JWT_SIGNING_KEY:
    JWT_SIGNING_KEY = SECRET_KEY
    logging.getLogger("config").warning(
        "JWT_SIGNING_KEY is not configured; falling back to SECRET_KEY. "
        "Disclosure of SECRET_KEY then also permits forging access tokens. "
        "Generate one with `python backend/utils/generate_secrets.py`."
    )

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ==============================================================================
