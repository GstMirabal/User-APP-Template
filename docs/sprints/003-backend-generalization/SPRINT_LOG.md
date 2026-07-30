# 📋 Sprint Log: #003 — Backend / Generalization
**Sprint ID**: 003
**Stack / Layer**: backend / generalization
**Date**: 2026-07-30
**Branch**: `ai-sprint/003` (RA-12)
**Commit**: ec5108c
**Status**: `CLOSED`

---

## 1. Purpose

Make the repository actually be the thing it claims to be: a generic Django user-management template. Sprint #001 made it verifiable, #002 made it defensible, this one removes the traces of the cryptocurrency project it was extracted from and documents what a consumer can safely strip.

## 2. Decision recorded

| ADR | Decision | Triggers |
| :--- | :--- | :--- |
| [ADR-0005](../../decisions/ADR-0005-generic-secret-vault.md) | Generic secret vault, without exchange-specific columns | 1, 2, 3 |

## 3. Work completed

| # | Item | Notes |
| :--- | :--- | :--- |
| P1-3 | Removed `api_key_binance_encrypted`, `api_key_binance_index`, `api_secret_binance_encrypted` | Migration `0007`, irreversible |
| — | Repointed `UserSecretSerializer` at `dni`, `phone_number`, `date_of_birth` | These were in the vault but reachable by no endpoint |
| P1-2 | Translated every Spanish string in code to English | Migration `0008`, metadata only |
| P1-4 | `VerificationService.setup_2fa` is now a `@staticmethod` | Was an undecorated instance method annotated as if `self` were a `User` |
| P1-5 | Deleted the Celery stub and the inert `send_welcome_email` closure | `config/celery_app.py` never existed |
| P1-7 | Split `settings.py` (704 lines) into a package of six modules | Verified equivalent, see §5 |
| P2-2 | `docs/guides/USERS_CUSTOMIZATION_GUIDE.md` | Core vs optional, with what breaks for each |
| P2-6 | Split `requirements.txt` into runtime and dev sets | A deployment was installing pytest |
| P2-10 | Refreshed the README | Documented the pre-#002 setup |
| — | Deleted `backend/scripts/test_encryption.py` | Manual script, redundant since the suite was restored in #001 |

## 4. The serializer question

Removing the exchange columns would have left `UserSecretSerializer` with no fields at all — and `PATCH /me/secrets/` is the endpoint guarded by verification plus step-up re-authentication, the most heavily protected write in the project. Deleting its only payload would have left the entire step-up machinery guarding nothing.

The vault already held `dni`, `phone_number` and `date_of_birth`, encrypted with blind indexes, exposed by no endpoint whatsoever. Repointing the serializer at those gives the endpoint a purpose every consumer of a user-management template shares, rather than one that served a single named third party.

## 5. Verifying the settings split

A 704-line module holding conditional security logic is not something to refactor on faith. Every resolved setting was dumped before the split and diffed against the result:

| | Count |
| :--- | ---: |
| Settings before | 198 |
| Settings after | 196 |
| Byte-identical | 196 |
| Absent after | 2 — `_TRUE_VALUES`, `_FALSE_VALUES`, private helpers of `_as_bool` that `import *` correctly does not export |
| Different | 1 — `LOGGING`, where `UTCFormatter`'s module path moved. Same class, same configuration. |

Two problems the split surfaced, both of the kind that fail far from their cause:

- **`BASE_DIR` was computed by counting `.parent` calls from `__file__`.** The extra package level made it resolve one directory short, and the symptom was `config.toml not found` — pointing at configuration rather than at path arithmetic. Now derived from a named anchor.
- **`email.py` and `logging.py` inside a package shadow the standard library modules** for any relative import. Renamed to `email_config.py` and `logging_config.py` before the hazard could bite.

## 6. Metrics

| Metric | #002 | #003 |
| :--- | ---: | ---: |
| Tests | 77 | 85 |
| `ruff` findings | 0 | 0 |
| `manage.py check` warnings | 0 | 0 |
| ADRs | 4 | 5 |
| Migrations | 6 | 8 |
| Spanish strings in code | 20 | 0 |
| Largest module | 704 lines (`settings.py`) | 239 lines (`settings/security.py`) |
| Graph | 3433 / 3613 | 3501 / 3674 |

## 7. Operator actions required

| Action | Why |
| :--- | :--- |
| Export any data in the `api_key_binance_*` / `api_secret_binance_*` columns **before** migrating | Migration `0007` drops them irreversibly (ADR-0005 §3) |
| `pip install -r requirements-dev.txt` for a development checkout | `requirements.txt` is now runtime-only |
| Run `make migrate` | Migrations `0007` and `0008` |

## 8. Deferred

- Retroactive ADRs for the inherited decisions still listed in each Blueprint §7 — encryption strategy, GDPR anonymisation, email-as-username (P1-8).
- Verification-code resend endpoint (P1-9) and RS256 evaluation (P1-10).
- Contract documents (P2-1), test-suite idiom unification (P2-7), repo-wide `ruff format` (P2-8).
- Historical `UserSecretAudit` rows still read `field_affected = "api_key_binance"`. Deliberately not rewritten: they are an accurate record of events that happened.

---
*Closed under RA-05: Blueprints, Global Roadmap, Walkthroughs, and Master Ledger all updated.*
