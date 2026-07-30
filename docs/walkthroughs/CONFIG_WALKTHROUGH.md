# 🏁 Walkthrough: CONFIG
**File**: `docs/walkthroughs/CONFIG_WALKTHROUGH.md` (RA-06 Option B naming)
**Last updated**: Sprint #000

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

## 2. Current state

Configuration loads and the project boots — `ruff`, `mypy`, and the Django app registry all resolve `config.settings` successfully. The security posture is genuinely strong for a template: the `DEBUG = False` branch covers the headers most projects forget, refresh tokens rotate and blacklist, and the process refuses to start without `MASTER_KEY` and `ENCRYPTION_PEPPER`.

Two structural concerns stand out. `settings.py` is a single 572-line module (ruff `PLR0915`) mixing secret resolution, security headers, third-party wiring, and logging in one file. It is *not* a graph god-node — measured degree centrality puts `apps/users/views.py` (111) and `apps/users/managers.py` (109) at the top, with `settings.py` outside the top eight — so the concern is module cohesion, not blast radius. And `SIMPLE_JWT["SIGNING_KEY"]` reuses Django's `SECRET_KEY`, so any disclosure of the session-signing secret is simultaneously a full JWT forgery capability.

Implements: `docs/architecture/CONFIG_BLUEPRINT.md`.

## 3. Known limitations / tech debt

| Item | Severity | Marked as | Tracked where |
| :--- | :--- | :--- | :--- |
| No `pytest-django` configuration in `pyproject.toml` (`DJANGO_SETTINGS_MODULE` / `pythonpath`), so the entire test suite is uncollectable. This is a `config`-owned defect with project-wide blast radius. | **Blocker** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| `SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY` — one secret serves both session signing and token forgery resistance; rotating either forces the other. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| `settings.py` is 572 lines in one module (ruff `PLR0915`), mixing secret resolution, security headers, third-party wiring, and logging. Cohesion concern, not a god-node. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1 |
| `ruff check backend/` reports **79 findings**: `E501` ×23, `RUF012` ×20, `PLC0415` ×15, `ERA001` ×6, `PTH*` ×8, `N806` ×2, `E402` ×2, `B904` ×2, `PLR0915` ×1. `agents.md §1 linter_command` rejects any exit code > 0, so the Quality Gate cannot currently pass. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| Two competing ruff configurations exist. `ruff --show-settings` confirms `ruff.toml` is authoritative, so the entire `[tool.ruff]` block in `pyproject.toml` — including its `ignore` list for `PLC0415`/`PLR0915` and its `select` set — is dead configuration. This is why ignored rules still surface. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1 |
| `B904` ×2 — `raise` inside `except` without `from`, losing the exception chain. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2 |
| `.npmrc` supply-chain controls (RA-10: `ignore-scripts=true`, `minimum-release-age=1440`) are absent. Currently moot — no JS/TS surface exists — but required the moment a frontend lands. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2 |
| `identity.config.json` declares `governed_by_agents: false` and leaves owner/project fields empty, though `.agents` is installed and active. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2 |

## 4. How to operate it

```bash
# Verify configuration resolves and the app registry loads
venv/bin/python backend/manage.py check

# Inspect the generated OpenAPI schema
venv/bin/python backend/manage.py spectacular --file schema.yml

# Confirm which ruff config is authoritative
venv/bin/ruff check backend/ --show-settings | head -5
```
---
*Updated at every Sprint Closeout touching this module (RA-05).*
