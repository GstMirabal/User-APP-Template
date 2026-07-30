"""Shared cache backend and the windows that depend on it (ADR-0001).

Part of the settings package. See `config/settings/__init__.py` for the load
order and why the split exists.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .security import *

# SECTION 6.5: CACHE CONFIGURATION
# ==============================================================================
# The cache is a security dependency, not just an optimisation (ADR-0001):
# TOTP anti-replay and step-up authentication both store short-lived state that
# must be visible to every worker. Django's implicit default is a per-process
# LocMemCache, under which neither control holds.
# ------------------------------------------------------------------------------
cache_config = config.get("cache", {})
REDIS_URL = cache_config.get("REDIS_URL") or os.environ.get("REDIS_URL")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
elif DEBUG:
    # Development convenience only. Single-process runserver, so per-process
    # state is equivalent to shared state.
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "user-app-template-dev",
        }
    }
else:
    raise ImproperlyConfigured(
        "CRITICAL: Running in PRODUCTION mode (DEBUG=False) but no REDIS_URL is "
        "configured. TOTP anti-replay and step-up authentication require a cache "
        "shared across workers; a per-process fallback would silently void both. "
        "Define REDIS_URL in the `[cache]` section of `config.toml`."
    )

# Window during which a re-authentication remains valid for step-up gated
# endpoints (ADR-0002). Deliberately short: it guards secret writes and
# irreversible anonymisation.
STEP_UP_WINDOW_SECONDS = int(cache_config.get("STEP_UP_WINDOW_SECONDS") or 300)

# Lifetime of a registration verification code (ADR-0004).
VERIFICATION_OTP_TTL_MINUTES = int(
    cache_config.get("VERIFICATION_OTP_TTL_MINUTES") or 15
)


# ==============================================================================
