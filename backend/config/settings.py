"""
==============================================================================

          PROFESSIONAL DJANGO PROJECT SETTINGS TEMPLATE

This file provides a robust, secure, and production-ready Django configuration.
It is designed as a generic foundation for any professional project, covering:
  - Dynamic path configuration, compatible with Docker and local development.
  - Secure loading of secrets and variables from a `config.toml` file.
  - A comprehensive set of security configurations following industry
    best practices.

This configuration serves as a production-ready template that demonstrates a
deep understanding of Django's operational and security architecture.

For more information on this file, see:
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see:
https://docs.djangoproject.com/en/5.2/ref/settings/

==============================================================================
"""

import datetime
import logging
import os
from datetime import UTC
from pathlib import Path
from typing import Any, override

import dj_database_url
import envtoml
from django.core.exceptions import ImproperlyConfigured


# ==============================================================================
# SECTION 1: BASE_DIR, CONFIGURATION PATH, AND ENVIRONMENT LOADING
# ==============================================================================
# Reliably establishes the project's root directory (`BASE_DIR`) and loads the
# main `config.toml` file.
# ------------------------------------------------------------------------------
default_base_dir = Path(__file__).resolve().parent.parent.parent
env_base_dir = os.environ.get('BASE_DIR')
BASE_DIR = Path(env_base_dir) if env_base_dir else default_base_dir
config_path = BASE_DIR / "config.toml"
env_path = BASE_DIR / ".env"

if env_path.exists():
    with env_path.open("r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip().strip("'").strip('"')

try:
    with config_path.open('r', encoding='utf-8') as f:
        config: Any = envtoml.load(f)
except FileNotFoundError as e:
    raise ImproperlyConfigured(
        f'FATAL: The configuration file "config.toml" was not found. '
        f'Expected location: {config_path}'
    ) from e


# ==============================================================================
# SECTION 2: CORE SECURITY SETTINGS
# ==============================================================================

# --- 2.1 SECRET KEY (SECRET_KEY) ---
# Ensures the application fails immediately if the SECRET_KEY is not configured.
# Documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#secret-key
# ------------------------------------------------------------------------------
try:
    SECRET_KEY = config['django_settings']['DJANGO_SECRET_KEY']
    if not SECRET_KEY:
        raise ValueError('DJANGO_SECRET_KEY must not be empty.')
except (KeyError, ValueError) as e:
    raise ImproperlyConfigured(
        'CRITICAL: The DJANGO_SECRET_KEY is missing or empty in your '
        f'config.toml / .env file. Error: {e}'
    ) from e


# --- 2.2 DEBUG MODE (DEBUG) ---
# SECURITY WARNING: Never run with debug turned on in production!
# Documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#debug
# ------------------------------------------------------------------------------
DEBUG = config['django_settings'].get('DEBUG')


# --- 2.3 ALLOWED HOSTS (ALLOWED_HOSTS) ---
# A critical security measure to prevent HTTP Host Header attacks.
# Documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#allowed-hosts
# ------------------------------------------------------------------------------
if DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
else:
    try:
        allowed_hosts_str = config['django_settings'].get('ALLOWED_HOSTS')
    except KeyError:
        allowed_hosts_str = None

    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(
        ',') if host.strip()] if allowed_hosts_str else []

if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'CRITICAL: Running in PRODUCTION mode (DEBUG=False) but '
        '`ALLOWED_HOSTS` is empty. Define it in the '
        '`[django_settings]` section of `config.toml`.'
    ) from None


# --- 2.4 ALLOWED ORIGINS FOR CORS (CORS_ALLOWED_ORIGINS) ---
# Controls which frontend domains can access this API.
# Documentation (django-cors-headers): https://github.com/adamchainz/django-cors-headers
# ------------------------------------------------------------------------------
if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000", "http://localhost:5173", "http://localhost:4200",
        "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://127.0.0.1:4200",
    ]
else:
    try:
        cors_origins_str = config['django_settings'].get(
            'CORS_ALLOWED_ORIGINS')
    except KeyError:
        cors_origins_str = None

    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_str.split(
        ',') if origin.strip()] if cors_origins_str else []

if not DEBUG and not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        'CRITICAL: Running in PRODUCTION mode (DEBUG=False) but '
        '`CORS_ALLOWED_ORIGINS` is empty. Define it in the '
        '`[django_settings]` section of `config.toml`.'
    ) from None


# --- 2.5 ENCRYPTION CONFIGURATION (MASTER_KEY, ENCRYPTION_PEPPER) ---
# Keys for application-level encryption and blind indexing.
# ------------------------------------------------------------------------------
try:
    security_config = config.get('security', {})
    MASTER_KEY = security_config.get('MASTER_KEY')
    ENCRYPTION_PEPPER = security_config.get('ENCRYPTION_PEPPER')

    if not MASTER_KEY or not ENCRYPTION_PEPPER:
        # Fallback to environment variables if not in config.toml (for flexibility)
        MASTER_KEY = MASTER_KEY or os.environ.get('MASTER_KEY')
        ENCRYPTION_PEPPER = ENCRYPTION_PEPPER or os.environ.get(
            'ENCRYPTION_PEPPER')

    if not MASTER_KEY:
        raise ValueError("MASTER_KEY must be set for encryption.")
    if not ENCRYPTION_PEPPER:
        raise ValueError("ENCRYPTION_PEPPER must be set for blind indexing.")

except (KeyError, ValueError) as e:
    # In production, this should be a hard failure.
    if not DEBUG:
        raise ImproperlyConfigured(
            f"CRITICAL: Encryption configuration failed. {e}"
        )
    else:
        # In DEBUG, we can warn or set dummy values if strictly necessary,
        # but better to fail early to ensure dev/prod parity.
        print(f"WARNING: Encryption keys missing in DEBUG mode. {e}")
        # For development convenience ONLY if you want to allow running without keys:
        # MASTER_KEY = b'some-default-dev-key-32-bytes-url-safe-base64'
        # ENCRYPTION_PEPPER = b'some-default-dev-pepper'
        # But let's stick to raising error to force proper setup.
        raise ImproperlyConfigured(f"Encryption keys missing. {e}")


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
    CSP_DEFAULT_SRC = ("'self'", )
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'no-referrer'
    SECURE_PERMISSIONS_POLICY = {
        'geolocation': '()', 'microphone': '()', 'camera': '()',
        'fullscreen': '()', 'payment': '()',
    }


# ==============================================================================
# SECTION 4: APPLICATION DEFINITION
# ==============================================================================
# Informs Django which applications are active. Organized into three tiers.
# Documentation: https://docs.djangoproject.com/en/5.2/ref/settings/#installed-apps
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django Core Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # --- Third Party Apps ---
    'corsheaders',
    'csp',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'axes',
    'drf_spectacular',
    # --- Local Apps ---
    'apps.core',
    'apps.users',
]


# ==============================================================================
# SECTION 5: MIDDLEWARE AND CORE CONFIGURATION
# ==============================================================================

# -- 5.1: Middleware --
# The request/response processing pipeline. Order is critical.
# Documentation: https://docs.djangoproject.com/en/5.2/ref/middleware/
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',  # Recommended to be placed high in the stack
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

# -- 5.2: Root URL Configuration --
# ------------------------------------------------------------------------------
ROOT_URLCONF = 'config.urls'

# -- 5.3: Template Configuration --
# ------------------------------------------------------------------------------
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

# -- 5.4: Application Server Entry Point --
# ------------------------------------------------------------------------------
WSGI_APPLICATION = 'config.wsgi.application'


# ==============================================================================
# SECTION 6: DATABASE CONFIGURATION
# ==============================================================================
# Assembles the database URL in Python for maximum control, reading components
# from the config object.
# Docs: https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# ------------------------------------------------------------------------------
try:
    db_components = config['DB']
    db_user = db_components.get('POSTGRES_USER')
    db_password = db_components.get('POSTGRES_PASSWORD')
    db_host = db_components.get('POSTGRES_HOST')
    db_port = db_components.get('POSTGRES_PORT')
    db_name = db_components.get('POSTGRES_DB')

    if not all([db_user, db_password, db_host, db_port, db_name]):
        raise ValueError(
            "One or more required database components are missing.")

    database_url = f"postgres://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
except (KeyError, ValueError) as e:
    raise ImproperlyConfigured(
        'CRITICAL: Database configuration failed. Check the [DB] section in '
        f'config.toml and .env file. Original error: {e}'
    ) from e


# ==============================================================================
# SECTION 7: PASSWORD VALIDATION AND HASHING
# ==============================================================================

# -- 7.1: Password Validators --
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'apps.core.validators.PasswordComplexityValidator'},
]

# -- 7.2: Password Hashers --
# https://docs.djangoproject.com/en/5.2/topics/auth/passwords/#password-storage
# ------------------------------------------------------------------------------
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# -- 7.3: Cookie and Session Security --
# ------------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'


# ==============================================================================
# SECTION 8: USER MODEL, INTERNATIONALIZATION, AND FILES
# ==============================================================================

# -- 8.1: Custom User Model --
# https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model
# ------------------------------------------------------------------------------
AUTH_USER_MODEL = 'users.User'

# -- 8.2: Internationalization (i18n) --
# https://docs.djangoproject.com/en/5.2/topics/i18n/
# ------------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True  # Saves datetimes in UTC in the DB.

# -- 8.3: Static and Media Files --
# https://docs.djangoproject.com/en/5.2/howto/static-files/
# ------------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'


# ==============================================================================
# SECTION 9: EMAIL CONFIGURATION
# ==============================================================================
# Dynamically configures the email backend based on the DEBUG flag.
# Docs: https://docs.djangoproject.com/en/5.2/topics/email/
# ------------------------------------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    try:
        email_config = config['email_settings']
        EMAIL_HOST = email_config['EMAIL_HOST']
        EMAIL_PORT = email_config['EMAIL_PORT']
        EMAIL_USE_TLS = email_config['EMAIL_USE_TLS']
        EMAIL_HOST_USER = email_config['EMAIL_HOST_USER']
        EMAIL_HOST_PASSWORD = email_config['EMAIL_HOST_PASSWORD']

        if not all([EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD]):
            raise ValueError(
                "EMAIL_HOST, EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD must not be empty in production."
            )
    except (KeyError, ValueError) as e:
        raise ImproperlyConfigured(
            'CRITICAL: Production email configuration failed. Check the '
            f'[email_settings] section in config.toml and .env. Original error: {e}'
        ) from e


# ==============================================================================
# SECTION 11: DJANGO REST FRAMEWORK & JWT CONFIGURATION
# ==============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
        "sensitive": "5/minute", # Para login/register
    },
}


# ==============================================================================
# SECTION 12: THIRD PARTY CONFIGURATIONS (AXES, SPECTACULAR)
# ==============================================================================

# -- 12.1: Authentication Backends (Axes) --
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# -- 12.2: Axes Settings (Brute Force Protection) --
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = datetime.timedelta(minutes=15)
AXES_LOCKOUT_TEMPLATE = None # Devuelve JSON vía DRF
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True

# -- 12.3: Spectacular Settings (OpenAPI) --
SPECTACULAR_SETTINGS = {
    'TITLE': 'User-APP-Template API',
    'DESCRIPTION': 'Security-first Identity and Authentication Template.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_PATCH': True,
    'COMPONENT_SPLIT_REQUEST': True,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ==============================================================================
# SECTION 12: DEFAULT PRIMARY KEY FIELD TYPE
# ==============================================================================
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==============================================================================
# SECTION 11: PROFESSIONAL LOGGING CONFIGURATION
# ==============================================================================
# Production-ready logging setup, adaptable to different environments.
# https://docs.djangoproject.com/en/5.2/topics/logging/
# ------------------------------------------------------------------------------

class UTCFormatter(logging.Formatter):
    """Custom logging formatter to ensure all timestamps are in UTC.

    Follows the ISO 8601 standard for unambiguous logging across environments.
    """

    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Runs the time formatting logic.

        Args:
            record (logging.LogRecord): The log record instance.
            datefmt (Optional[str]): The format string for the timestamp.

        Returns:
            str: The ISO 8601 formatted timestamp in UTC.
        """
        dt = datetime.datetime.fromtimestamp(record.created, tz=UTC)
        return dt.strftime(datefmt or '%Y-%m-%dT%H:%M:%SZ')


try:
    logs_dir_str = config['project_logging'].get('PROJECT_LOGS_DIR')
    if logs_dir_str:
        logs_dir = Path(logs_dir_str)
        logs_dir.mkdir(parents=True, exist_ok=True)
    else:
        raise ValueError("PROJECT_LOGS_DIR is not defined in config.toml")
except (KeyError, ValueError) as e:
    raise ImproperlyConfigured(f"Logging directory setup failed. Error: {e}")


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{levelname} [{name}] {message}', 'style': '{'},
        'verbose': {
            '()': UTCFormatter,
            'format': '{levelname} {asctime} {module} [{funcName}:{lineno}] {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(module)s %(lineno)d %(message)s'
        },
    },
    'handlers': {
        'console': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'simple'},
        'project_log_file': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': logs_dir / 'project.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'project_json_file': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': logs_dir / 'project.json',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'project_log_file', 'project_json_file'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
        'project': {
            'handlers': ['console', 'project_log_file', 'project_json_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
# ------------------------------------------------------------------------------
