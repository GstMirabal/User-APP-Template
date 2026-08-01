# 🗺️ Global Roadmap: django-users-app
**Last Audit Sprint**: #004
**Last Audit Date**: 2026-08-01
**Last Audit Commit SHA**: 0a71a8c

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

### Sprint #003 — generalization

| # | Item | ADR |
| :--- | :--- | :--- |
| P1-2 | Every Spanish string in code translated to English | — |
| P1-3 | Exchange-specific columns removed; vault and endpoint generalised | ADR-0005 |
| P1-4 | `setup_2fa` is a `@staticmethod` | — |
| P1-5 | Celery stub and inert closure deleted | — |
| P1-7 | `settings.py` split into a package of six modules | — |
| P2-2 | Customization guide: identity core vs optional extras | — |
| P2-6 | `requirements.txt` split into runtime and development sets | — |
| P2-10 | README refreshed for the current setup | — |

**No P0 items remain open.**

## P1 — Structural debt (Sprint #004)

| # | Item | Module |
| :--- | :--- | :--- |
| P1-8 | Author the retroactive ADRs still listed in the Blueprint §7 (encryption strategy, GDPR anonymization, email-as-username). | `users` |
| P1-9 | Verification-code resend endpoint with its own rate limiting. Expiry now exists, so an expired code currently needs administrator re-issue. | `users` |
| P1-11 | **No key rotation path.** `get_fernet()` builds a plain `Fernet(MASTER_KEY)` and `generate_blind_index()` reads a single `ENCRYPTION_PEPPER`, so changing either makes every stored secret undecryptable and every blind index unsearchable, with no supported migration. `MultiFernet` accepts a key list and decrypts under any of them while encrypting under the first, which is the mechanism a rotation would need. Verified by reading `users/encryption.py`; documented as a warning in the contract meanwhile. | `users` |

## P2 — Hygiene

| # | Item | Module |
| :--- | :--- | :--- |
| P2-5 | Add `.npmrc` with `ignore-scripts=true` and `minimum-release-age=1440` before any JS/TS surface lands (RA-10). | root |
| P2-7 | Unify the test suite on the pytest idiom, replace `assertTrue(True)` with real assertions, resolve the hardcoded `/2fa/activate/` URL. | `users` |
| P2-8 | Apply `ruff format` repo-wide as a standalone mechanical commit, then enable `ruff format --check` as a CI gate. | all |

### Closed by the Sprint #004 restructuring

| # | Item | Why it no longer applies |
| :--- | :--- | :--- |
| P1-10 | Evaluate RS256 instead of symmetric HS256. | JWT is configured by the host, not here. The reasoning is preserved in the contract under *Strongly recommended*. |
| P2-1 | Write `docs/contracts/{USERS,CORE,CONFIG}_CONTRACT.md`. | `USERS_CONTRACT.md` written; the `core` and `config` modules left this repository. |
| P2-9 | Restrict `/health/` at the ingress. | The endpoint moved to `Django-Pro-Template` along with the rest of the scaffolding. |

## Upstream (`.agents` framework)

| # | Item | Status |
| :--- | :--- | :--- |
| U-1 | `on_commit.py` secret scanner matched the bare substring `PASSWORD =`, blocking every commit touching authentication code while catching no real leak. Now requires a string *literal* assigned to a secret-named identifier, and additionally detects `MASTER_KEY`, `SIGNING_KEY` and `ENCRYPTION_PEPPER`. | ✅ Pushed to `origin/fix/secret-scanner-false-positives` (`624a6b4`). Open a PR against the `.agents` default branch when convenient. |
| U-2 | **`code_containers` cannot exclude the `.agents` submodule.** `docs_freshness_check.py` derives containers by prefix-matching each graph node's `source_file` against a declared `root`. A repository whose code sits at the root — as this one does since Sprint #004 — must declare `root: "."`, which then matches the 2698 `.agents/**` nodes and reports a phantom container `app/agents` as needing C4 Level 3. Narrowing to `root: "users/"` is worse: `container_for_source` skips files sitting directly under the root, which would drop the two highest-degree nodes in the graph (`views.py`, `managers.py`). Neither option is correct, so an `exclude` list — or an implicit skip of submodule paths — belongs in the checker. | Draft for the `.agents` nucleus (P6) |

## Open questions

| Question | Owner |
| :--- | :--- |
| Should `.agents` remain pinned to the personal `GstMirabal/.agents` remote, or track a separate upstream nucleus? | Human |
| Is a per-device step-up scope needed? The current grant is per user and applies to all their concurrent sessions (ADR-0002 §3). | Human |

---
*Updated at every Sprint Closeout (RA-05). Items move to a Sprint folder when scheduled, never executed directly from this file.*
