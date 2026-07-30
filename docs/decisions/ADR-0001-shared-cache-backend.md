# 📜 ADR-0001: Redis as the shared cache backend
**Status**: `Accepted`
**Date**: 2026-07-30
**Triggers**: 3, 6 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

No `CACHES` setting existed anywhere in the project, so Django fell back to its default `LocMemCache`. Three behaviours followed from that, all verified in the Sprint #000 audit:

- `VerificationService.verify_2fa` guards against TOTP replay by writing a `totp_used_<user_id>_<token>` key. `LocMemCache` is a per-process dictionary, so under any multi-worker deployment (Gunicorn, uWSGI, more than one container) a replayed token routed to a different worker finds an empty cache and is accepted.
- `HealthCheckView`'s docstring stated it checked "Cache (Redis)". It exercised an in-process dictionary that cannot fail independently of the application, so the probe reported `OK` unconditionally.
- The string "Redis" appeared nowhere in the project except two comments. `docker-compose.yml` declared only a PostgreSQL service.

TOTP anti-replay is a security control. The project ships two-factor authentication as a headline feature, and that control did not hold in the deployment topology the template is otherwise written for.

## 2. Decision

Add a Redis service to `docker-compose.yml` and declare `CACHES` explicitly, resolved from `config.toml` with an environment-variable fallback, following the pattern already used for the database.

In `DEBUG`, fall back to `LocMemCache` when no Redis URL is configured, so a developer can run the project without the extra container. Outside `DEBUG`, a missing cache configuration is a hard startup failure, matching how `SECRET_KEY`, `MASTER_KEY` and `ALLOWED_HOSTS` already behave.

`HealthCheckView` keeps probing `django.core.cache`, which now resolves to the real backend, and its docstring stops naming a specific technology.

## 3. Consequences

**Easier.** TOTP anti-replay holds across workers. The health probe reports on something that can actually fail. Step-up authentication for stateless JWT clients (ADR-0002) becomes implementable, since it needs shared server-side state with a TTL. Celery, if ever wired, has a broker available.

**Harder.** The template now has two infrastructure dependencies instead of one. Redis becomes a single point of failure for two-factor login: if it is unreachable outside `DEBUG`, TOTP verification and step-up both fail closed. That is the correct direction for a security control, but it is real operational surface that a consumer of this template must plan for.

The development fallback means dev and production differ in cache semantics. A replay bug reachable only across processes will not reproduce locally. This is deliberate — requiring Redis to run the test suite would be a worse trade — but it is why the anti-replay test asserts on cache interaction rather than on process topology.

## 4. Deciders

Repository owner, on the recommendation of the Sprint #000 audit.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **Redis service + explicit `CACHES`** (chosen) | Anti-replay holds across workers; health probe becomes meaningful; unblocks JWT step-up and Celery | Second infrastructure dependency; new failure mode for 2FA |
| Declare `CACHES` as `LocMemCache` explicitly, document that production needs a shared backend | Zero new infrastructure; honest about the limitation | Leaves a security control broken by default; a template that documents its own hole rather than closing it |
| Database-backed cache (`django.core.cache.backends.db`) | No new service; shared across workers | Writes a row per TOTP attempt on the hot authentication path; the database is already the scarcer resource |
| Move anti-replay into a model table instead of the cache | Durable, no cache needed | Requires a migration and manual expiry sweeping; reimplements TTL semantics the cache provides natively |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`).*
