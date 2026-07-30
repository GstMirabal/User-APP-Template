# 🏛️ Blueprint: CONFIG
**File**: `docs/architecture/CONFIG_BLUEPRINT.md` (RA-06 Option B naming)
**Status**: `DRAFT`
**Sprint of origin**: #000
**Last Audit Sprint**: #002
**Last Audit Date**: 2026-07-30
**Last Audit Commit SHA**: aa4e5db

---

arc42-lite (`rules/documentation_standard.md §5`) — Reference only. This document states current facts, verifiably; it never argues for them. Any decision behind this module's shape lives in a linked ADR, not here.

## 1. Introduction & Goals

The `config` module is the Django project root: it resolves configuration from `config.toml` with environment-variable fallback, enforces the production security posture (HSTS, CSP, secure cookies), wires authentication (SimpleJWT + Axes), declares the DRF throttling policy, mounts the root URLConf, and exposes the WSGI/ASGI entrypoints. It also owns the UTC-normalized structured logging configuration.

## 2. Context & Scope

| Aspect | Value |
| :--- | :--- |
| **Upstream dependencies** | `envtoml` + `config.toml`, `dj_database_url`, `django`, `rest_framework`, `rest_framework_simplejwt`, `axes`, `csp`, `corsheaders`, `drf_spectacular`. |
| **Downstream consumers** | Every runtime component. `apps.users` and `apps.core` read `AUTH_USER_MODEL`, `MASTER_KEY`, `ENCRYPTION_PEPPER`, cache and throttle settings from here. |

## 3. Building Block View

| Aspect | Value |
| :--- | :--- |
| **Owns** | `backend/config/` — `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`. |
| **Must not touch** | `backend/apps/*/` business logic, `backend/utils/`, application migrations. |

Contracts (formal interfaces this module exposes):

| Interface | Type | Auth | Defined in |
| :--- | :--- | :--- | :--- |
| `POST /api/v1/auth/token/` | REST (SimpleJWT) | `AllowAny` | `docs/contracts/CONFIG_CONTRACT.md` |
| `POST /api/v1/auth/token/refresh/` | REST (SimpleJWT) | `AllowAny` | `docs/contracts/CONFIG_CONTRACT.md` |
| `GET /api/schema/` | OpenAPI 3.0 document | `AllowAny` | `drf-spectacular` |
| `GET /api/docs/swagger/`, `GET /api/docs/redoc/` | HTML docs UI | `AllowAny` | `drf-spectacular` |
| `/admin/` | Django admin | staff session | `django.contrib.admin` |

Routing table (`backend/config/urls.py`):

| Prefix | Target |
| :--- | :--- |
| `/admin/` | Django admin site |
| `/health/` | `apps.core.views.HealthCheckView` |
| `/api/v1/auth/` | SimpleJWT obtain/refresh |
| `/api/v1/users/` | `apps.users.urls` |
| `/api/schema/`, `/api/docs/` | `drf-spectacular` |

Data model: none — configuration only.

## 4. Runtime View

**Flow 1 — Boot and secret resolution**
1. `settings.py` loads `config.toml` via `envtoml`.
2. `MASTER_KEY` / `ENCRYPTION_PEPPER` are read from the `security` section, falling back to `os.environ`.
3. If either is still unset, boot aborts with `ValueError` — the process never starts with encryption unconfigured.

**Flow 2 — Production hardening (`DEBUG = False` branch)**
Applies `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS = 31536000` with subdomains and preload, `CSP_DEFAULT_SRC = ("'self'",)`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY = "no-referrer"`, and a permissions policy.

**Flow 3 — Authentication**
1. `AUTHENTICATION_BACKENDS` places `axes.backends.AxesBackend` ahead of `ModelBackend`, so lockout is evaluated first.
2. Axes locks after 5 failures on the user+IP combination, with a 15-minute cooloff, reset on success, returning JSON (no lockout template).
3. On success SimpleJWT issues an HS256 access token (30 min) signed with `SECRET_KEY`, plus a rotating refresh token (1 day) blacklisted after rotation.

**Flow 4 — Request throttling**
`AnonRateThrottle` 100/day, `UserRateThrottle` 1000/day, and the named `sensitive` scope at 5/minute consumed by `users` for registration, verification, and re-authentication.

**Flow 5 — Logging**
`UTCFormatter` overrides `formatTime` so every record is emitted in UTC regardless of `TIME_ZONE` (`Europe/Madrid`).

## 5. Crosscutting Concepts

| Concept | Implementation |
| :--- | :--- |
| **Configuration precedence** | `config.toml` first, environment variable second, hard failure third. Secrets are never committed — `config.toml.example` is the tracked shape. |
| **Middleware ordering** | `SecurityMiddleware` → `CSPMiddleware` → session → CORS → common → CSRF → auth → messages → clickjacking → `AxesMiddleware` (last, so `request.user` is resolved before lockout accounting). |
| **UTC-normalized logs** | Storage and logs are UTC (`USE_TZ = True`); only presentation uses `Europe/Madrid`. |
| **Schema-first API docs** | `drf-spectacular` `AutoSchema` with `COMPONENT_SPLIT_REQUEST`/`COMPONENT_SPLIT_PATCH`, so request and response components stay distinct. |

## 6. Non-negotiable Constraints

| Constraint | Verification |
| :--- | :--- |
| The process must not boot without `MASTER_KEY` and `ENCRYPTION_PEPPER`. | Unset both and run `make dev` — expect `ValueError` at import time. |
| Secrets must never be read into agent context. | `agents.md §3 secret_sovereignty` / RA-09: use `make` targets or a subshell `source`, never a direct read of `.env`. |
| DRF must default to authenticated access. | `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == ("rest_framework.permissions.IsAuthenticated",)`. |
| Axes must be evaluated before the model backend. | `AUTHENTICATION_BACKENDS[0] == "axes.backends.AxesBackend"`. |
| Refresh tokens must rotate and blacklist. | `SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]` and `["BLACKLIST_AFTER_ROTATION"]` are both `True`. |
| Production must serve HSTS for one year with preload. | `SECURE_HSTS_SECONDS == 31536000` in the `DEBUG = False` branch. |
| Production must not run on a per-process cache. | Boot fails when `DEBUG=False` and no `REDIS_URL` is set; CI asserts the resolved backend. |
| The JWT signing key must differ from `SECRET_KEY`. | CI production smoke asserts `SIMPLE_JWT["SIGNING_KEY"] != SECRET_KEY`. |
| `DEBUG` must be a real boolean, never a truthy string. | `_as_bool()` coerces it and rejects anything ambiguous; the CI production smoke step asserts `settings.DEBUG is False`. |
| A real environment variable must override a `.env` entry. | `.env` loading uses `os.environ.setdefault`. |

## 7. Decisions

This module's ADR log — link, don't restate. No ADRs exist yet:

- `docs/decisions/ADR-0001-shared-cache-backend.md`: Redis as the shared cache; a per-process fallback voided TOTP anti-replay.
- `docs/decisions/ADR-0003-separate-jwt-signing-key.md`: `JWT_SIGNING_KEY` separated from `SECRET_KEY`.
- _(pending)_ `config.toml` (via `envtoml`) as primary configuration source with env fallback — trigger #4.
- _(pending)_ `settings.py` as a single 572-line module rather than a split settings package — no ADR trigger fires (measured degree centrality places it outside the backend top eight, so trigger #5 does not apply); recorded as a cohesion concern in `docs/walkthroughs/CONFIG_WALKTHROUGH.md §3`.

## 8. Glossary

| Term | Meaning in this module |
| :--- | :--- |
| **Sensitive scope** | The `ScopedRateThrottle` bucket rated 5/minute, applied to authentication-adjacent endpoints. |
| **Cooloff** | The 15-minute window during which Axes refuses further attempts for a locked user+IP pair. |
| **Blind spot of `DEBUG`** | Security headers in the `DEBUG = False` branch are inactive in development; only production exercises them. |

---
*A module without a ratified Blueprint cannot enter Execution (agents.md §0). C4 Level 3 not evaluated — `backend/config/` sits outside the declared `code_containers` root `backend/apps/` (`rules/documentation_standard.md §2.1`).*
