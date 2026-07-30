# 🏁 Walkthrough: USERS
**File**: `docs/walkthroughs/USERS_WALKTHROUGH.md` (RA-06 Option B naming)
**Last updated**: Sprint #003

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
| #002 | Step-up reachable via JWT | Grant resolves through session or shared cache (ADR-0002); token clients can finally reach gated endpoints. |
| #002 | Verification code secured | Own Fernet-encrypted column with expiry, constant-time compare, audit entry (ADR-0004). |
| #002 | Credentials use a CSPRNG | OTP and 2FA recovery codes moved off `random`. |
| #002 | Admin secret leak closed | `UserSecretInline` converted from deny-list to allow-list of derived indicators. |
| #002 | `/me/reauth/` under Axes | Re-authentication routed through the authentication backend, so lockout applies. |
| #003 | Vault generalised | Exchange columns removed; `/me/secrets/` now writes `dni`, `phone_number`, `date_of_birth` (ADR-0005). |
| #003 | Module in English | Every `verbose_name`, `__str__`, docstring and comment translated. |
| #003 | Celery stub deleted | The framework was never wired; tasks ran synchronously behind a stub. |

## 2. Current state

The identity domain is feature-complete, verified, and — as of Sprint #002 — no longer carrying the security defects the audit found. 77 tests pass against an in-RAM database.

Step-up authentication works for both client styles. This is the headline change: `PATCH /me/secrets/` and `POST /me/anonymize/` were unreachable for every bearer-token client, which is the project's own primary authentication mechanism. `/me/reauth/` now re-authenticates through the auth backend, so Axes counts failed attempts against it.

The registration code has its own Fernet-encrypted column with an expiry, is compared in constant time, is recorded in `UserSecretAudit`, and is never logged. Issuing one no longer destroys a stored exchange credential. Both the code and the 2FA recovery codes come from `secrets` rather than `random`.

The admin exposes derived booleans and timestamps only; no stored secret value reaches the DOM.

What remains open is genericity rather than security: exchange-specific columns, Spanish strings, and the half-wired Celery stub. All are Sprint #003 work.

Implements: `docs/architecture/USERS_BLUEPRINT.md`.

## 3. Known limitations / tech debt

| Item | Severity | Marked as | Tracked where |
| :--- | :--- | :--- | :--- |
| No resend endpoint for an expired verification code; recovery is administrator re-issue. Needs its own rate limiting. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1-9 |
| A step-up grant is keyed by user id, so it applies to every concurrent session of that user, and survives the client discarding its token until the window lapses (ADR-0002 §3). | Medium | `:tech-debt:` | `ADR-0002` |
| `test_api.py` hardcodes `/api/v1/users/me/2fa/activate/` because `reverse()` does not resolve that nested router action. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2-7 |

**Resolved in Sprint #003**: exchange-specific columns; Spanish strings; Celery stub; `setup_2fa` shape.

**Resolved in Sprint #002**: step-up unreachable via JWT; OTP plaintext in a credential column; OTP never expiring; OTP in logs; `random` for credentials; `/me/reauth/` outside Axes; admin ciphertext exposure.

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
