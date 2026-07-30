# 🏁 Walkthrough: USERS
**File**: `docs/walkthroughs/USERS_WALKTHROUGH.md` (RA-06 Option B naming)
**Last updated**: Sprint #001

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
| #001 | Admin repaired | `two_factor_enabled` moved to the `User` fieldset it belongs to; user pages render again. |
| #001 | Suite made executable | The nine pre-existing tests ran for the first time and all passed; factories added. |

## 2. Current state

The identity domain is feature-complete and, as of Sprint #001, **actually verified**. The suite runs (52 tests, all passing) against an in-RAM database. The nine pre-existing tests turned out to be correct all along — they had simply never been executed, because no `DJANGO_SETTINGS_MODULE` existed anywhere in the project.

Models, managers, serializers, permissions and `UserViewSet` are coherent; the encryption helpers are correct and well documented. The admin renders again after `UserProfileInline` stopped declaring a field belonging to `User`, and a custom system check (`core.E001`) now makes that class of defect a startup error.

What remains open is security design rather than correctness: step-up authentication is session-bound and therefore unreachable for stateless JWT clients, the registration OTP is stored in plaintext inside an exchange-credential column, and TOTP anti-replay depends on a per-process cache. All three are Sprint #002 work.

Implements: `docs/architecture/USERS_BLUEPRINT.md`.

## 3. Known limitations / tech debt

| Item | Severity | Marked as | Tracked where |
| :--- | :--- | :--- | :--- |
| Step-up authentication stores its timestamp in the Django **session**, but DRF also accepts stateless `JWTAuthentication`. A pure-JWT client has no session, so `PATCH /me/secrets/` and `POST /me/anonymize/` are permanently unreachable for it. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0-4 |
| `VerificationService.initialize_verification_flow` stores the registration OTP inside `api_key_binance_encrypted` — a field reserved for an exchange credential — and writes it in **plaintext**, bypassing `set_sensitive_data()`. No expiry exists. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0-5 |
| `/me/reauth/` calls `check_password()` directly instead of going through the authentication backend, so `AxesBackend` never counts the attempt. Password guessing there is limited only by the 5/min throttle. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0-8 |
| `UserSecretInline` excludes only three fields, so `dni_encrypted`, `date_of_birth_encrypted`, `phone_number_encrypted` and `otp_recovery_codes` ciphertext still render in the admin DOM despite the "paranoid" docstring. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0-9 |
| TOTP anti-replay relies on the default per-process `LocMemCache`; a replayed token hitting a different worker succeeds. | **High** | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P0-7 |
| `api_key_binance_*` / `api_secret_binance_*` columns are exchange-specific residue in a generic user-management template. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1-3 |
| `VerificationService.setup_2fa(self: User)` is an undecorated instance method annotated as if `self` were a `User`, yet invoked as `VerificationService.setup_2fa(user)`. Every sibling is a `@staticmethod`. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1-4 |
| Spanish strings in `verbose_name`, `__str__` and comments across the module — violates `agents.md §1 code_logic`. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1-2 |
| Celery is a stub: `config/celery_app.py` does not exist, so `tasks.py` falls back to `CeleryStub` and every task runs synchronously. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1-5 |
| `test_api.py` hardcodes `/api/v1/users/me/2fa/activate/` because `reverse()` does not resolve that nested router action. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2-7 |

**Resolved in Sprint #001**: admin `FieldError`; uncollectable test suite; discarded application logs (including this module's replay-attack warning and anonymization audit trail); mid-file imports in `permissions.py`.

## 4. How to operate it

```bash
# Bring up PostgreSQL (host port 5434)
make db-up

# Apply migrations
make migrate

# Run the development server
make dev

# Lint (clean)
venv/bin/ruff check backend/

# Tests — 52 passing, in-RAM SQLite, no Docker required
make test
```
---
*Updated at every Sprint Closeout touching this module (RA-05).*
