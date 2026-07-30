# 🏁 Walkthrough: CORE
**File**: `docs/walkthroughs/CORE_WALKTHROUGH.md` (RA-06 Option B naming)
**Last updated**: Sprint #001

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| pre-#000 | Password complexity validator | Four coded rules (upper, lower, digit, symbol) registered in `AUTH_PASSWORD_VALIDATORS`. |
| pre-#000 | Health endpoint | `/health/` probing PostgreSQL and the cache independently. |
| #000 | Retroactive documentation | Module reverse-engineered into `docs/architecture/CORE_BLUEPRINT.md`. |
| #001 | Health endpoint repaired | `status=` replaces the invalid `status_code=`; healthy and degraded paths both covered by tests. |
| #001 | Admin-integrity system check | `apps/core/checks.py` (`core.E001`) constructs every registered admin form and inline formset at startup. |

## 2. Current state

Both components work and are covered by tests.

`PasswordComplexityValidator` is correct, documented in Google style, and wired into `AUTH_PASSWORD_VALIDATORS`.

`HealthCheckView` returns 200 with every dependency reachable and 503 when either the database or the cache fails, each probed independently. The `status_code=` defect is fixed and pinned by three tests.

`apps/core/checks.py` adds what Django does not provide: a check that actually builds every registered `ModelAdmin` form and `InlineModelAdmin` formset. It reports a `FieldError` as `core.E001` and any other construction failure as `core.W001`, since the latter may be an artefact of the check's request stub rather than a real defect.

Implements: `docs/architecture/CORE_BLUEPRINT.md`.

## 3. Known limitations / tech debt

| Item | Severity | Marked as | Tracked where |
| :--- | :--- | :--- | :--- |
| The cache probe reports on Django's default `LocMemCache`, which is per-process and always healthy. It cannot detect a real shared backend being down. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0-7 |
| `test_config.py` still mixes Django `TestCase` with the pytest idiom used everywhere else, and `test_settings_load_correctly` asserts `True`. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2-7 |

## 4. How to operate it

```bash
# Start the stack
make db-up && make dev

# Probe the health endpoint (200 healthy, 503 degraded)
curl -i http://127.0.0.1:8000/health/

# Verify the password validator rules
venv/bin/python -c "from apps.core.validators import PasswordComplexityValidator as V; print(V().get_help_text())"
```
---
*Updated at every Sprint Closeout touching this module (RA-05).*
