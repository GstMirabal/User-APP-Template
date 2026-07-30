# 🏁 Walkthrough: USERS
**File**: `docs/walkthroughs/USERS_WALKTHROUGH.md` (RA-06 Option B naming)
**Last updated**: Sprint #000

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| pre-#000 | Custom identity model | `User` with UUID PK and email login, plus `Address`, shipped before governance adoption. |
| pre-#000 | Satellite auto-provisioning | `post_save` signal atomically creates `UserProfile` + `UserSecret` on registration. |
| pre-#000 | Encrypted PII vault | Fernet encryption + HMAC-SHA256 blind indexing via `backend/utils/encryption.py`. |
| pre-#000 | TOTP two-factor | Enrolment, recovery codes, anti-replay cache, drift window ±1. |
| pre-#000 | GDPR anonymization | Irreversible PII erasure through `SoftDeleteQuerySet.anonymize()`. |
| pre-#000 | Audit trail | `UserSecretAudit` append-only log; `AuditManager` blocks physical deletion. |
| #000 | Retroactive documentation | Module reverse-engineered into `docs/architecture/USERS_BLUEPRINT.md`. |

## 2. Current state

The identity domain is feature-complete on paper and structurally coherent: models, managers, serializers, permissions, and the `UserViewSet` all exist and import cleanly, and the encryption helpers are correct and well-documented. **However, none of it is currently verified by an executable test.** `make test` cannot collect a single test — `pytest` aborts at import with `ImproperlyConfigured: Requested setting AUTH_USER_MODEL, but settings are not configured`, because no `DJANGO_SETTINGS_MODULE` / `pytest-django` configuration exists in `pyproject.toml`. The 144 lines in `backend/apps/users/tests.py` have therefore never run in this configuration.

Implements: `docs/architecture/USERS_BLUEPRINT.md`.

## 3. Known limitations / tech debt

| Item | Severity | Marked as | Tracked where |
| :--- | :--- | :--- | :--- |
| Test suite cannot be collected — no `pytest-django` / `DJANGO_SETTINGS_MODULE` config. The module has zero executable verification. | **Blocker** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| Step-up authentication stores its timestamp in the Django **session**, but DRF also accepts stateless `JWTAuthentication`. A pure-JWT client has no session, so `PATCH /me/secrets/` and `POST /me/anonymize/` are permanently unreachable for it. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| `VerificationService.initialize_verification_flow` stores the registration OTP inside `api_key_binance_encrypted` — a field reserved for an exchange credential. Registering a user overwrites any stored Binance key, and `verify_account` then blanks it. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| The registration OTP is written to that field in **plaintext** (`OTP_PENDING:<code>`), bypassing `set_sensitive_data()` and therefore Fernet encryption, into a column named `_encrypted`. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0 |
| `api_key_binance_*` / `api_secret_binance_*` columns are exchange-specific leftovers from the pre-rebrand codebase, inside a project positioned as a generic IAM template. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1 |
| `VerificationService.setup_2fa(self: User)` is an undecorated instance method annotated as if `self` were a `User`, yet invoked as `VerificationService.setup_2fa(user)`. It works only because the class attribute resolves to a plain function; every sibling method is a `@staticmethod`. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1 |
| Spanish strings in `verbose_name`, `__str__`, and comments across `models/profile.py`, `models/secrets.py`, `tasks.py`, `urls.py`, `serializers/registration.py` — violates `agents.md §1 code_logic` (artifacts strictly English). | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1 |
| Celery is a stub: `config/celery_app.py` does not exist, so `tasks.py` falls back to a `CeleryStub` and every task runs synchronously as a plain function. The `send_welcome_email` closure in `signals.py` has a `pass` body. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1 |
| `backend/apps/users/permissions.py:41` places `import` statements mid-file, after class definitions (ruff `E402`). | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2 |
| Stale comment at `views.py:174` still says step-up will be added "inside the Step-Up Phase 3", though `RequiresStepUp` is already wired in `get_permissions`. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2 |

No ADRs exist yet to justify any of the above as deliberate; see `USERS_BLUEPRINT.md §7` for the retroactive ADR candidates.

## 4. How to operate it

```bash
# Bring up PostgreSQL (host port 5434)
make db-up

# Apply migrations
make migrate

# Run the development server
make dev

# Lint (currently 79 findings across backend/)
venv/bin/ruff check backend/

# Tests — CURRENTLY FAILS TO COLLECT, see §3
make test
```
---
*Updated at every Sprint Closeout touching this module (RA-05).*
