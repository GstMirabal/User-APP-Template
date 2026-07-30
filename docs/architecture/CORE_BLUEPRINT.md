# 🏛️ Blueprint: CORE
**File**: `docs/architecture/CORE_BLUEPRINT.md` (RA-06 Option B naming)
**Status**: `DRAFT`
**Sprint of origin**: #000
**Last Audit Sprint**: #003
**Last Audit Date**: 2026-07-30
**Last Audit Commit SHA**: ec5108c

---

arc42-lite (`rules/documentation_standard.md §5`) — Reference only. This document states current facts, verifiably; it never argues for them. Any decision behind this module's shape lives in a linked ADR, not here.

## 1. Introduction & Goals

The `core` module holds cross-cutting primitives that belong to no single business domain: the liveness/readiness endpoint that probes the database and cache, and the password complexity validator wired into Django's `AUTH_PASSWORD_VALIDATORS`. It declares no models of its own.

## 2. Context & Scope

| Aspect | Value |
| :--- | :--- |
| **Upstream dependencies** | `django.db.connections`, `django.core.cache`, `django.core.exceptions.ValidationError`, `rest_framework`. |
| **Downstream consumers** | `backend/config/urls.py` (mounts `HealthCheckView` at `/health/`), `backend/config/settings.py` (registers `PasswordComplexityValidator`), transitively every registration/password-change path in `users`. |

## 3. Building Block View

| Aspect | Value |
| :--- | :--- |
| **Owns** | `backend/apps/core/` — `views.py`, `validators.py`, `checks.py`, `admin.py`, `apps.py`, `models.py` (empty), `tests/`. |
| **Must not touch** | `backend/apps/users/`, `backend/config/settings.py`, `backend/utils/`. |

Contracts (formal interfaces this module exposes):

| Interface | Type | Auth | Defined in |
| :--- | :--- | :--- | :--- |
| `GET /health/` | REST | `AllowAny` | `docs/contracts/CORE_CONTRACT.md` |
| `PasswordComplexityValidator.validate()` | Function (Django validator protocol) | n/a | `backend/apps/core/validators.py` |
| `core.E001` / `core.W001` | Django system check | n/a | `backend/apps/core/checks.py` |

Data model: none. `backend/apps/core/models.py` is intentionally empty.

## 4. Runtime View

**Flow 1 — Health check**
1. `GET /health/` → `HealthCheckView.get`.
2. Opens a cursor on the `default` database connection; on exception marks `database: DOWN`, `system: DEGRADED`, HTTP 503.
3. Writes and reads back a `health_check` cache key (5 s TTL); on exception or read-back failure marks `cache: DOWN`, `system: DEGRADED`, HTTP 503.
4. Returns the accumulated status map.

**Flow 2 — Password validation**
1. Django calls `PasswordComplexityValidator.validate(password, user)` during registration and password change.
2. Four regex rules run in order — uppercase, lowercase, digit, special character (`[\W_]`) — each raising `ValidationError` with its own error code (`password_no_upper`, `password_no_lower`, `password_no_digit`, `password_no_symbol`).
3. `get_help_text()` supplies the requirement summary rendered in forms.

## 5. Crosscutting Concepts

| Concept | Implementation |
| :--- | :--- |
| **Fail-degraded health reporting** | Each dependency is probed independently; one failing subsystem degrades the response without masking the other's status. |
| **Coded validation errors** | Every complexity rule raises a distinct `code`, so clients can localize messages rather than parse English strings. |
| **Broad exception capture with logging** | `HealthCheckView` catches bare `Exception` per probe but always logs at `ERROR` — satisfying `agents.md §1 exception_handling` (no silent `pass`). |

## 6. Non-negotiable Constraints

| Constraint | Verification |
| :--- | :--- |
| `/health/` must never require authentication. | `HealthCheckView.permission_classes == [AllowAny]`. |
| A degraded dependency must return HTTP 503, never 200. | `GET /health/` with the database container stopped (`make db-down`). |
| Password rules must be enforced server-side, not only client-side. | `PasswordComplexityValidator` is listed in `AUTH_PASSWORD_VALIDATORS` (`backend/config/settings.py:325`). |
| This module must declare no models. | `backend/apps/core/models.py` stays empty; `apps/core/migrations/` must not appear. |
| Every registered admin form and inline formset must be constructible. | `manage.py check` reports `core.E001` otherwise. |

## 7. Decisions

This module's ADR log — link, don't restate. No ADRs exist yet:

- _(pending)_ Combined liveness+readiness in a single unauthenticated endpoint — trigger #6 (availability/reliability boundary).

## 8. Glossary

| Term | Meaning in this module |
| :--- | :--- |
| **DEGRADED** | At least one probed dependency is unreachable; the service answers but cannot be trusted for full traffic. |
| **Probe** | A single dependency check (database cursor, cache round-trip) contributing one key to the health response. |

---
*A module without a ratified Blueprint cannot enter Execution (agents.md §0). C4 Level 3 not required here — `core` density 1.78 falls below the qualifying `users` container in the `backend` stack (`rules/documentation_standard.md §2.1`).*
