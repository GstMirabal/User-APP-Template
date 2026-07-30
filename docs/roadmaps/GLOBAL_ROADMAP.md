# 🗺️ Global Roadmap: User-APP-Template
**Last Audit Sprint**: #002
**Last Audit Date**: 2026-07-30
**Last Audit Commit SHA**: aa4e5db

---

Backlog derived from the Sprint #000 reverse-engineering audit and extended by findings surfaced during execution. Every item traces to a verified finding in a Walkthrough §3 — nothing here is speculative. Priorities are execution order, not importance rankings.

## ✅ Completed

### Sprint #001 — verification capability

| # | Item |
| :--- | :--- |
| P0-1 | Executable test harness (in-RAM SQLite); suite 0 → 52 |
| P0-2 | `HealthCheckView` returns 200/503 instead of raising `TypeError` |
| P0-3 | Zero `ruff` findings; configuration unified in `ruff.toml` |
| P0-10 | Admin `FieldError` fixed; `core.E001` system check prevents recurrence |
| P0-11 | Application logging reaches handlers |
| P0-12 | Production mode reachable — `DEBUG` boolean coercion |
| — | CI pipeline gating lint, checks, tests, production smoke |

### Sprint #002 — security

| # | Item | ADR |
| :--- | :--- | :--- |
| P0-4 | Step-up authentication reachable for stateless JWT clients | ADR-0002 |
| P0-5 | Verification OTP in its own encrypted column, with expiry | ADR-0004 |
| P0-6 | JWT signing key separated from `SECRET_KEY` | ADR-0003 |
| P0-7 | Redis as shared cache; TOTP anti-replay holds across workers | ADR-0001 |
| P0-8 | `/me/reauth/` routed through the auth backend, so Axes applies | — |
| P0-9 | `UserSecretInline` converted to an allow-list | — |
| P0-13 | Verification code no longer logged | ADR-0004 |
| P0-14 | OTP and 2FA recovery codes moved off `random` to `secrets` | — |
| P1-6 | `pwned-passwords-django` wired into the validator chain | — |

**No P0 items remain open.**

## P1 — Structural debt (Sprint #003)

| # | Item | Module |
| :--- | :--- | :--- |
| P1-2 | Translate every Spanish string in code to English (`agents.md §1 code_logic`). | `users` |
| P1-3 | Remove the `api_key_binance_*` / `api_secret_binance_*` columns. Destructive migration → **ADR** (trigger #1). `preferred_currency` stays: an ordinary user preference, not crypto residue. | `users` |
| P1-4 | Make `VerificationService.setup_2fa` a `@staticmethod` taking `user: User`, matching its siblings. | `users` |
| P1-5 | Delete the Celery stub and the inert `send_welcome_email` closure. A template should not ship half-wired async infrastructure. | `users` |
| P1-7 | Split `settings.py` (620 lines) into a `config/settings/` package: `base`, `security`, `cache`, `third_party`, `logging`. | `config` |
| P1-8 | Author the retroactive ADRs still listed in each Blueprint §7 (encryption strategy, GDPR anonymization, email-as-username). | all |
| P1-9 | Verification-code resend endpoint with its own rate limiting. Expiry now exists, so an expired code currently needs administrator re-issue. | `users` |
| P1-10 | Evaluate RS256 with a key pair. HS256 is symmetric: any verifying service must hold the minting key. Warrants its own ADR. | `config` |

## P2 — Hygiene

| # | Item | Module |
| :--- | :--- | :--- |
| P2-1 | Write the contract documents referenced by the Blueprints: `docs/contracts/{USERS,CORE,CONFIG}_CONTRACT.md`. | all |
| P2-2 | `docs/guides/USERS_CUSTOMIZATION_GUIDE.md` — which parts are the identity core and which are optional extras, so consumers can strip with confidence. | `users` |
| P2-5 | Add `.npmrc` with `ignore-scripts=true` and `minimum-release-age=1440` before any JS/TS surface lands (RA-10). | root |
| P2-6 | Split `requirements.txt` into runtime and development sets; it mixes `pytest`, `factory-boy` and `ruff` with production dependencies. | root |
| P2-7 | Unify the test suite on the pytest idiom, replace `assertTrue(True)` with real assertions, resolve the hardcoded `/2fa/activate/` URL. | `core`, `users` |
| P2-8 | Apply `ruff format` repo-wide as a standalone mechanical commit, then enable `ruff format --check` as a CI gate. | all |
| P2-9 | Consider restricting `/health/` at the ingress; it is unauthenticated and names which subsystem is degraded. | `core` |
| P2-10 | README still documents the pre-#002 setup: no Redis service, no `[cache]` section, no `JWT_SIGNING_KEY`. | root |

## Upstream (`.agents` framework)

| # | Item | Status |
| :--- | :--- | :--- |
| U-1 | `on_commit.py` secret scanner matched the bare substring `PASSWORD =`, blocking every commit touching authentication code while catching no real leak. Now requires a string *literal* assigned to a secret-named identifier, and additionally detects `MASTER_KEY`, `SIGNING_KEY` and `ENCRYPTION_PEPPER`. | ✅ Fixed on `fix/secret-scanner-false-positives`; **needs pushing to the `.agents` remote** |

## Open questions

| Question | Owner |
| :--- | :--- |
| Should `.agents` remain pinned to the personal `GstMirabal/.agents` remote, or track a separate upstream nucleus? | Human |
| Is a per-device step-up scope needed? The current grant is per user and applies to all their concurrent sessions (ADR-0002 §3). | Human |

---
*Updated at every Sprint Closeout (RA-05). Items move to a Sprint folder when scheduled, never executed directly from this file.*
