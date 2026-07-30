# 🗺️ Global Roadmap: User-APP-Template
**Last Audit Sprint**: #001
**Last Audit Date**: 2026-07-30
**Last Audit Commit SHA**: 86cc29b

---

Backlog derived from the Sprint #000 reverse-engineering audit and extended by findings surfaced during Sprint #001. Every item traces to a verified finding in a Walkthrough §3 — nothing here is speculative. Priorities are execution order, not importance rankings.

## ✅ Completed in Sprint #001

| # | Item | Verified by |
| :--- | :--- | :--- |
| P0-1 | Executable test harness (`[tool.pytest.ini_options]`, `config/settings_test.py`, in-RAM SQLite) | Suite went 0 → 52 passing |
| P0-2 | `HealthCheckView` returns 200/503 instead of raising `TypeError` | 3 regression tests |
| P0-3 | Zero `ruff` findings; configuration unified in `ruff.toml` | `ruff check backend/` clean |
| P0-10 | Admin `FieldError` fixed; `core.E001` system check prevents recurrence | 3 check tests + 4 admin smoke tests |
| P0-11 | Application logging reaches handlers | 6 logging tests |
| P0-12 | Production mode reachable — `DEBUG` boolean coercion | 15 coercion tests + CI smoke step |
| — | CI pipeline (`.github/workflows/ci.yml`) | Gates lint, checks, tests, production smoke |

## P0 — Security blockers (Sprint #002)

Each of these requires an ADR before implementation (`rules/documentation_standard.md §3.1`, trigger #3 — security boundary — escalating to full MADR).

| # | Item | Module |
| :--- | :--- | :--- |
| P0-4 | Make step-up authentication work for stateless JWT clients. Session-bound today, so `/me/secrets/` and `/me/anonymize/` are unreachable for them. **Decision taken: hybrid** — session when present, cache key with TTL otherwise. | `users` |
| P0-5 | Give the registration OTP its own encrypted field with an expiry, instead of overwriting `api_key_binance_encrypted` in plaintext. Route it through `set_sensitive_data()`. | `users` |
| P0-6 | Separate `SIMPLE_JWT["SIGNING_KEY"]` from `SECRET_KEY`. | `config` |
| P0-7 | Declare `CACHES` and add Redis to `docker-compose.yml`. Unblocks cross-worker TOTP anti-replay and makes the health probe test a real backend. **Decision taken: Redis in compose.** | `config`, `core` |
| P0-8 | Route `/me/reauth/` through `django.contrib.auth.authenticate()` so `AxesBackend` counts failed attempts. | `users` |
| P0-9 | Convert `UserSecretInline` to an explicit allow-list. A deny-list leaks again the moment a column is added. | `users` |
| P0-13 | Stop logging the OTP value. Harmless while logs were discarded; a live leak now that they are not. | `users` |

## P1 — Structural debt (Sprint #003)

| # | Item | Module |
| :--- | :--- | :--- |
| P1-2 | Translate every Spanish string in code to English (`agents.md §1 code_logic`). | `users` |
| P1-3 | Remove the `api_key_binance_*` / `api_secret_binance_*` columns. Destructive migration → **ADR** (trigger #1). `preferred_currency` stays: it is an ordinary user preference, not crypto residue. | `users` |
| P1-4 | Make `VerificationService.setup_2fa` a `@staticmethod` taking `user: User`, matching its siblings. | `users` |
| P1-5 | Delete the Celery stub and the inert `send_welcome_email` closure. A template should not ship half-wired async infrastructure. | `users` |
| P1-6 | Wire `pwned-passwords-django` into `AUTH_PASSWORD_VALIDATORS` — already a dependency, currently unused. | `config` |
| P1-7 | Split `settings.py` (572 lines) into a `config/settings/` package: `base`, `security`, `third_party`, `logging`. | `config` |
| P1-8 | Author the retroactive ADRs listed in each Blueprint §7. The inherited architecture has zero recorded rationale. | all |

## P2 — Hygiene

| # | Item | Module |
| :--- | :--- | :--- |
| P2-1 | Write the contract documents referenced by the Blueprints: `docs/contracts/{USERS,CORE,CONFIG}_CONTRACT.md`. | all |
| P2-2 | `docs/guides/USERS_CUSTOMIZATION_GUIDE.md` — which parts are the identity core and which are optional extras, so consumers can strip with confidence. | `users` |
| P2-5 | Add `.npmrc` with `ignore-scripts=true` and `minimum-release-age=1440` before any JS/TS surface lands (RA-10). | root |
| P2-6 | Split `requirements.txt` into runtime and development sets; it currently mixes `pytest`, `factory-boy` and `ruff` with production dependencies. | root |
| P2-7 | Unify the test suite on the pytest idiom, replace `assertTrue(True)` with real assertions, and resolve the hardcoded `/2fa/activate/` URL. | `core`, `users` |
| P2-8 | Apply `ruff format` repo-wide as a standalone mechanical commit, then enable `ruff format --check` as a CI gate. | all |

## Upstream (`.agents` framework)

| # | Item | Status |
| :--- | :--- | :--- |
| U-1 | `on_commit.py` secret scanner matched the bare substring `PASSWORD =`, blocking every commit touching authentication code while catching no real leak. Now requires a string *literal* assigned to a secret-named identifier, and additionally detects `MASTER_KEY`, `SIGNING_KEY` and `ENCRYPTION_PEPPER`. | ✅ Fixed on `fix/secret-scanner-false-positives`; **needs pushing to the `.agents` remote** |

## Open questions

| Question | Owner |
| :--- | :--- |
| Should `.agents` remain pinned to the personal `GstMirabal/.agents` remote, or track a separate upstream nucleus? | Human |

---
*Updated at every Sprint Closeout (RA-05). Items move to a Sprint folder when scheduled, never executed directly from this file.*
