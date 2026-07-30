"""Test settings.

Imports the real configuration and overrides only what must not touch external
infrastructure, so the suite runs without Docker or a reachable PostgreSQL.

`agents.md §3 local_testing` mandates instantiating the database in RAM rather
than against the native URL. Everything else — middleware, authentication
backends, password validators, throttling — stays exactly as production
defines it, so the tests exercise the real stack.
"""

from .settings import *  # noqa: F403

# In-RAM database (agents.md §3 local_testing). SQLite covers every field type
# this project uses: UUIDField, JSONField and GenericIPAddressField.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Local cache so TOTP anti-replay and health probes never reach a shared broker
# during tests. Each run gets its own namespace.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "user-app-template-test",
    }
}

# The breach-corpus validator performs an outbound HTTPS request. Tests must
# not depend on network reachability, so it is dropped here; the production
# validator list is asserted separately.
AUTH_PASSWORD_VALIDATORS = [
    validator
    for validator in AUTH_PASSWORD_VALIDATORS  # noqa: F405
    if "PwnedPasswords" not in validator["NAME"]
]

# Argon2 is deliberately slow; tests create many users and do not measure
# hashing strength. The production hasher list is asserted separately.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Keep log files out of the test run; handlers stay wired so tests can assert
# that application loggers actually resolve to one.
LOGGING["handlers"]["project_log_file"]["class"] = "logging.NullHandler"  # noqa: F405
LOGGING["handlers"]["project_json_file"]["class"] = "logging.NullHandler"  # noqa: F405
for _handler in ("project_log_file", "project_json_file"):
    for _key in ("filename", "maxBytes", "backupCount"):
        LOGGING["handlers"][_handler].pop(_key, None)  # noqa: F405
