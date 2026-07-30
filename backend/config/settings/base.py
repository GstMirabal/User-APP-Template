"""Project foundations: configuration loading, apps, middleware, database.

Part of the settings package. See `config/settings/__init__.py` for the load
order and why the split exists.
"""

import os
from pathlib import Path
from typing import Any

import dj_database_url
import envtoml
from django.core.exceptions import ImproperlyConfigured

# ==============================================================================
# SECTION 1: BASE_DIR, CONFIGURATION PATH, AND ENVIRONMENT LOADING
# ==============================================================================
# Reliably establishes the project's root directory (`BASE_DIR`) and loads the
# main `config.toml` file.
# ------------------------------------------------------------------------------
# This file is backend/config/settings/base.py, so the repository root is four
# levels up. Named explicitly rather than counting `.parent` calls, which is
# what silently broke when this module moved into a package.
_SETTINGS_DIR = Path(__file__).resolve().parent
default_base_dir = _SETTINGS_DIR.parent.parent.parent
env_base_dir = os.environ.get("BASE_DIR")
BASE_DIR = Path(env_base_dir) if env_base_dir else default_base_dir
config_path = BASE_DIR / "config.toml"
env_path = BASE_DIR / ".env"

if env_path.exists():
    with env_path.open("r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, _, value = line.partition("=")
                # setdefault, not assignment: a variable already present in the
                # real environment wins over the file. Overwriting it would let
                # a stray .env silently override the values injected into a
                # container or CI runner.
                os.environ.setdefault(
                    key.strip(), value.strip().strip("'").strip('"')
                )

try:
    with config_path.open("r", encoding="utf-8") as f:
        config: Any = envtoml.load(f)
except FileNotFoundError as e:
    raise ImproperlyConfigured(
        f'FATAL: The configuration file "config.toml" was not found. '
        f"Expected location: {config_path}"
    ) from e


# ==============================================================================
# SECTION 4: APPLICATION DEFINITION
# ==============================================================================
# Informs Django which applications are active. Organized into three tiers.
# Documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#installed-apps
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django Core Apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # --- Third Party Apps ---
    "corsheaders",
    "csp",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "axes",
    "drf_spectacular",
    # --- Local Apps ---
    "apps.core",
    "apps.users",
]


# ==============================================================================
# SECTION 5: MIDDLEWARE AND CORE CONFIGURATION
# ==============================================================================

# -- 5.1: Middleware --
# The request/response processing pipeline. Order is critical.
# Documentation: https://docs.djangoproject.com/en/5.2/ref/middleware/
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",  # Recommended to be placed high in the stack
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

# -- 5.2: Root URL Configuration --
# ------------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"

# -- 5.3: Template Configuration --
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# -- 5.4: Application Server Entry Point --
# ------------------------------------------------------------------------------
WSGI_APPLICATION = "config.wsgi.application"


# ==============================================================================
# SECTION 6: DATABASE CONFIGURATION
# ==============================================================================
# Assembles the database URL in Python for maximum control, reading components
# from the config object.
# Docs: https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# ------------------------------------------------------------------------------
try:
    db_components = config["DB"]
    db_user = db_components.get("POSTGRES_USER")
    db_password = db_components.get("POSTGRES_PASSWORD")
    db_host = db_components.get("POSTGRES_HOST")
    db_port = db_components.get("POSTGRES_PORT")
    db_name = db_components.get("POSTGRES_DB")

    if not all([db_user, db_password, db_host, db_port, db_name]):
        raise ValueError("One or more required database components are missing.")

    database_url = f"postgres://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
except (KeyError, ValueError) as e:
    raise ImproperlyConfigured(
        "CRITICAL: Database configuration failed. Check the [DB] section in "
        f"config.toml and .env file. Original error: {e}"
    ) from e


# ==============================================================================
# SECTION 8: USER MODEL, INTERNATIONALIZATION, AND FILES
# ==============================================================================

# -- 8.1: Custom User Model --
# https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model
# ------------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"

# -- 8.2: Internationalization (i18n) --
# https://docs.djangoproject.com/en/5.2/topics/i18n/
# ------------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True  # Saves datetimes in UTC in the DB.

# -- 8.3: Static and Media Files --
# https://docs.djangoproject.com/en/5.2/howto/static-files/
# ------------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"


# ==============================================================================
# SECTION 12: DEFAULT PRIMARY KEY FIELD TYPE
# ==============================================================================
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==============================================================================
