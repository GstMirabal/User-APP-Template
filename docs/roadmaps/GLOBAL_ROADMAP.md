# 🗺️ Global Roadmap: User-APP-Template
**Last Audit Sprint**: #000
**Last Audit Date**: 2026-07-30
**Last Audit Commit SHA**: b27b5c2

---

Backlog derived from the Sprint #000 Scenario C reverse-engineering audit. Every item traces to a verified finding in a Walkthrough §3 — nothing here is speculative. Priorities are execution order, not importance rankings.

## P0 — Blockers (the Quality Gate cannot pass until these clear)

| # | Item | Module | Evidence |
| :--- | :--- | :--- | :--- |
| P0-1 | Restore an executable test harness: add `[tool.pytest.ini_options]` with `DJANGO_SETTINGS_MODULE = "config.settings"` and `pythonpath = ["backend"]`, install `pytest-django`, and point `make test` at the whole suite rather than one file. | `config` | `pytest` aborts at collection with `ImproperlyConfigured`. |
| P0-2 | Fix `HealthCheckView.get` — replace the invalid `status_code=` kwarg with `status=`, and rename the local `status` dict so it stops shadowing the DRF `status` module. | `core` | DRF `Response.__init__` has no `status_code` parameter; `/health/` returns 500 unconditionally. |
| P0-3 | Clear the 79 `ruff` findings (or justify each ignore in the authoritative `ruff.toml`). | all | `agents.md §1 linter_command` rejects exit code > 0. |
| P0-4 | Decide and implement a step-up mechanism that works under stateless JWT — the session-backed timestamp is unreachable for JWT-only clients, making `/me/secrets/` and `/me/anonymize/` dead endpoints for them. **Requires an ADR** (trigger #3). | `users` | `RequiresStepUp` reads `request.session`; DRF also accepts `JWTAuthentication`. |
| P0-5 | Give the registration OTP its own storage instead of overwriting `api_key_binance_encrypted`, and route it through `set_sensitive_data()` so it is actually encrypted. **Requires an ADR** (trigger #3). | `users` | `VerificationService.initialize_verification_flow` writes plaintext `OTP_PENDING:<code>` into an `_encrypted` column. |
| P0-6 | Separate `SIMPLE_JWT["SIGNING_KEY"]` from `SECRET_KEY`. **Requires an ADR** (trigger #3). | `config` | One secret currently serves both session signing and JWT forgery resistance. |

## P1 — Structural debt

| # | Item | Module |
| :--- | :--- | :--- |
| P1-1 | Remove the `[tool.ruff]` block from `pyproject.toml` (dead config) or consolidate onto it and delete `ruff.toml`. One authority, not two. | `config` |
| P1-2 | Translate every Spanish string in code — `verbose_name`, `__str__`, docstrings, comments — to English per `agents.md §1 code_logic`. | `users` |
| P1-3 | Generalize or remove the `api_key_binance_*` / `api_secret_binance_*` columns; they are exchange-specific residue in a generic IAM template. Requires a migration → **ADR** (trigger #1). | `users` |
| P1-4 | Make `VerificationService.setup_2fa` a `@staticmethod` with a correct `user: User` parameter, matching its siblings. | `users` |
| P1-5 | Wire Celery properly (`config/celery_app.py` + broker) or delete the stub and the dead `send_welcome_email` closure. Half-wired async is worse than none. | `users` |
| P1-6 | Add the missing type hints on `HealthCheckView.get` (`agents.md §1 Types`). | `core` |
| P1-7 | Split `settings.py` (572 lines) into a settings package by concern: base, security, third-party, logging. | `config` |
| P1-8 | Author the retroactive ADRs listed in each Blueprint §7 — the inherited architecture currently has zero recorded rationale. | all |

## P2 — Hygiene

| # | Item | Module |
| :--- | :--- | :--- |
| P2-1 | Move the mid-file imports in `permissions.py:41-43` to the top (`E402` ×2). | `users` |
| P2-2 | Add `from` to the two bare re-raises inside `except` blocks (`B904`). | `users`, `utils` |
| P2-3 | Delete the stale `views.py:174` comment promising step-up in "Phase 3" — already implemented. | `users` |
| P2-4 | Populate `identity.config.json` and set `governed_by_agents: true`. | root |
| P2-5 | Add `.npmrc` with `ignore-scripts=true` and `minimum-release-age=1440` before any JS/TS surface lands (RA-10). | root |
| P2-6 | Write the contract documents referenced by the Blueprints: `docs/contracts/{USERS,CORE,CONFIG}_CONTRACT.md`. | all |

## Deferred / open questions

| Question | Owner |
| :--- | :--- |
| Is this repository intended as a reusable template or as a running product? The answer changes whether P1-3 is a deletion or a generalization. | Human |
| Should `.agents` remain pinned to the personal `GstMirabal/.agents` remote, or track an upstream nucleus? | Human |

---
*Updated at every Sprint Closeout (RA-05). Items move to a Sprint folder when scheduled, never executed directly from this file.*
