# 🏁 Walkthrough: CORE
**File**: `docs/walkthroughs/CORE_WALKTHROUGH.md` (RA-06 Option B naming)
**Last updated**: Sprint #000

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| pre-#000 | Password complexity validator | Four coded rules (upper, lower, digit, symbol) registered in `AUTH_PASSWORD_VALIDATORS`. |
| pre-#000 | Health endpoint | `/health/` probing PostgreSQL and the cache independently. |
| #000 | Retroactive documentation | Module reverse-engineered into `docs/architecture/CORE_BLUEPRINT.md`. |

## 2. Current state

`PasswordComplexityValidator` is correct and thoroughly documented in Google style; it is wired into settings and runs on every registration.

`HealthCheckView` is **broken at runtime**. `backend/apps/core/views.py:44` returns `Response(status, status_code=status_code)`, but DRF's `Response.__init__` signature is `(self, data=None, status=None, template_name=None, headers=None, exception=False, content_type=None)` — there is no `status_code` keyword. Every request to `/health/` therefore raises `TypeError` and yields HTTP 500, including the healthy path. Verified by inspecting the installed DRF signature in `venv/`.

Implements: `docs/architecture/CORE_BLUEPRINT.md`.

## 3. Known limitations / tech debt

| Item | Severity | Marked as | Tracked where |
| :--- | :--- | :--- | :--- |
| `HealthCheckView.get` passes an invalid `status_code=` kwarg to DRF `Response`; `/health/` returns HTTP 500 unconditionally. Also shadows the module-level name `status` (the DRF status module) with a local dict. | **Blocker** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| `HealthCheckView.get` has no type hints on `request` or its return value — violates `agents.md §1 Types` (mandatory hints on all args and return values). | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1 |
| `backend/apps/core/tests.py` (59 lines) cannot be collected — same missing `pytest-django` configuration as `users`. | **Blocker** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| A degraded-dependency response has never been exercised, since the endpoint fails before reaching it. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1 |

## 4. How to operate it

```bash
# Start the stack
make db-up && make dev

# Probe the health endpoint (currently returns 500 — see §2)
curl -i http://127.0.0.1:8000/health/

# Verify the password validator rules
venv/bin/python -c "from apps.core.validators import PasswordComplexityValidator as V; print(V().get_help_text())"
```
---
*Updated at every Sprint Closeout touching this module (RA-05).*
