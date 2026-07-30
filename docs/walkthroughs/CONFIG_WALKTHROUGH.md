# 🏁 Walkthrough: CONFIG
**File**: `docs/walkthroughs/CONFIG_WALKTHROUGH.md` (RA-06 Option B naming)
**Last updated**: Sprint #001

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| pre-#000 | TOML-first configuration | `config.toml` via `envtoml`, with environment-variable fallback and hard failure on missing crypto keys. |
| pre-#000 | Production security posture | HSTS (1 year, preload), CSP, secure/HttpOnly/SameSite cookies, nosniff, `no-referrer`. |
| pre-#000 | Brute-force protection | `django-axes` first in `AUTHENTICATION_BACKENDS`, 5 failures / 15-minute cooloff, user+IP combination. |
| pre-#000 | JWT session management | SimpleJWT HS256, 30-minute access, 1-day rotating refresh with blacklist. |
| pre-#000 | OpenAPI 3.0 surface | `drf-spectacular` with Swagger and Redoc UIs. |
| pre-#000 | UTC-normalized logging | `UTCFormatter` overriding `formatTime`. |
| #000 | Retroactive documentation | Module reverse-engineered into `docs/architecture/CONFIG_BLUEPRINT.md`. |
| #001 | Production mode made reachable | Explicit boolean coercion for `DEBUG`; the whole `if not DEBUG:` hardening block now executes. |
| #001 | Application logging repaired | `apps` and `utils` logger prefixes registered against the existing handlers. |
| #001 | Test harness restored | `settings_test.py` + `[tool.pytest.ini_options]`; suite runs on in-RAM SQLite. |
| #001 | ruff configuration unified | `ruff.toml` is the single authority; 79 findings to zero. |

## 2. Current state

Configuration loads, the project boots, and `manage.py check --fail-level WARNING` exits clean.

The security posture is genuinely strong for a template — HSTS with preload, CSP, secure/HttpOnly/SameSite cookies, Argon2 hashing with a 12-character minimum, rotating and blacklisted refresh tokens, and a hard refusal to start without `MASTER_KEY` and `ENCRYPTION_PEPPER`. **As of Sprint #001 that posture is also reachable.** It previously was not: `DEBUG` arrived as a string and was used unconverted, so `DEBUG=False` stayed truthy and the entire `if not DEBUG:` block was dead code. CI now boots with `DEBUG=False` on every run and asserts the hardening actually applies.

One structural concern remains. `settings.py` is a single 572-line module mixing secret resolution, security headers, third-party wiring and logging. It is *not* a graph god-node — measured degree centrality puts `apps/users/views.py` (111) and `apps/users/managers.py` (109) at the top, with `settings.py` outside the top eight — so this is cohesion, not blast radius. And `SIMPLE_JWT["SIGNING_KEY"]` still reuses Django's `SECRET_KEY`, so disclosure of the session-signing secret is simultaneously a full JWT forgery capability.

Implements: `docs/architecture/CONFIG_BLUEPRINT.md`.

## 3. Known limitations / tech debt

| Item | Severity | Marked as | Tracked where |
| :--- | :--- | :--- | :--- |
| `SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY` — one secret serves both session signing and token forgery resistance; rotating either forces the other. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0-6 |
| No `CACHES` block, so Django falls back to per-process `LocMemCache`. TOTP anti-replay does not hold across workers. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0-7 |
| `settings.py` is 572 lines in one module, mixing secret resolution, security headers, third-party wiring and logging. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1-7 |
| `ruff format --check` is not yet a CI gate: the codebase predates this formatter configuration and would need a repo-wide reformat first. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2-8 |
| `.npmrc` supply-chain controls (RA-10) are absent. Moot while no JS/TS surface exists; required the moment a frontend lands. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2-5 |

**Resolved in Sprint #001**: test harness restored; application logging repaired; production mode made reachable; `.env` precedence corrected; ruff configuration unified (79 findings to zero); deprecated Axes setting replaced; `identity.config.json` populated.

## 4. How to operate it

```bash
# Verify configuration resolves and the app registry loads
venv/bin/python backend/manage.py check

# Inspect the generated OpenAPI schema
venv/bin/python backend/manage.py spectacular --file schema.yml

# Lint (single authority: ruff.toml)
venv/bin/ruff check backend/

# Full suite (in-RAM SQLite, no Docker needed)
venv/bin/python -m pytest -q
```
---
*Updated at every Sprint Closeout touching this module (RA-05).*
