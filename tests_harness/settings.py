"""Minimal Django settings for running this app's own test suite.

This is not a project. It is the smallest configuration under which `users`
can be exercised, and it doubles as executable documentation of what the app
actually requires from a host — anything absent here is something the app does
not depend on.

A real project supplies its own settings; see `docs/contracts/USERS_CONTRACT.md`,
"Host requirements".
"""

import secrets
from pathlib import Path

from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent

# Generated per run for the same reason as MASTER_KEY below: nothing in this
# file should be a value a reader could mistake for one worth copying.
SECRET_KEY = secrets.token_urlsafe(64)
DEBUG = True
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "axes",
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "tests_harness.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# In-RAM database (agents.md section 3 local_testing).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "users-app-harness",
    }
}

# The app ships a custom user model, so a host cannot install it into a project
# that already has auth data.
AUTH_USER_MODEL = "users.User"

# Fernet key and blind-index pepper, generated fresh for each run.
#
# These were literals until Sprint #004. They were never real secrets, but a
# committed Fernet key is indistinguishable from a live one to a scanner, to a
# reader, and — the part that matters — to whoever copies this file as the
# starting point for a real host, which is exactly what it is documented as.
# They would have inherited a key published on GitHub for encrypting personal
# data.
#
# Generating them here also proves something the literals could not: the app
# derives everything from these settings and holds no key of its own, since a
# value that changes on every run cannot have been baked in anywhere.
MASTER_KEY = Fernet.generate_key().decode()
ENCRYPTION_PEPPER = secrets.token_hex(32)

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_FAILURE_LIMIT = 5
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
# A host requirement, not an app default — the app cannot set this for you.
# From axes 8 the default is derived from `get_user_model().USERNAME_FIELD`
# (`email` here), while Django's `AuthenticationForm` always names its field
# `username`. Unset, axes then records every admin/LoginView failure as
# `username=None` and lockout silently degrades to per-IP. The older default
# (a literal `"username"`, up to 6.5.1) needed nothing here, which is why
# requirements.txt floors axes at 8.3: one behaviour to document, not two. See
# docs/contracts/USERS_CONTRACT.md, "Host requirements".
AXES_USERNAME_FORM_FIELD = "username"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_RATES": {"sensitive": "5/minute"},
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

STATIC_URL = "static/"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Deliberately NOT set: STEP_UP_WINDOW_SECONDS and VERIFICATION_OTP_TTL_MINUTES.
# The app must work on its own defaults when a host does not declare them, and
# the suite passing here is what proves it.
