# 🏛️ Blueprint: USERS
**File**: `docs/architecture/USERS_BLUEPRINT.md` (RA-06 Option B naming)
**Status**: `DRAFT`
**Sprint of origin**: #000
**Last Audit Sprint**: #003
**Last Audit Date**: 2026-07-30
**Last Audit Commit SHA**: ec5108c

---

arc42-lite (`rules/documentation_standard.md §5`) — Reference only. This document states current facts, verifiably; it never argues for them. Any decision behind this module's shape lives in a linked ADR, not here.

## 1. Introduction & Goals

The `users` module is the identity domain of django-users-app. It owns the custom `User` model (UUID primary key, email as login field), two satellite models auto-created by signal (`UserProfile` for preferences and legal consent, `UserSecret` for encrypted PII and credentials), and the REST surface for registration, self-service profile management, TOTP two-factor enrolment, step-up re-authentication, and GDPR anonymization. It also owns the soft-delete and audit manager layer that keeps deleted records queryable without exposing them to normal reads.

## 2. Context & Scope

| Aspect | Value |
| :--- | :--- |
| **Upstream dependencies** | `users/encryption.py` (Fernet + HMAC blind index), the host's settings (`MASTER_KEY`, `ENCRYPTION_PEPPER`, `AUTH_USER_MODEL`), `django.contrib.auth`, `rest_framework`, `rest_framework_simplejwt`, `pyotp`, Django cache framework. |
| **Downstream consumers** | The host's root URLconf, which includes `users.urls` at a prefix of its choosing, `axes` (via `AUTHENTICATION_BACKENDS`), Django admin, any external API client. |

## 3. Building Block View

| Aspect | Value |
| :--- | :--- |
| **Owns** | `users/` — `models/`, `serializers/`, `tests/`, `views.py`, `managers.py`, `permissions.py`, `services.py`, `signals.py`, `step_up.py`, `admin.py`, `urls.py`, `migrations/`, plus `encryption.py`, `defaults.py`, `events.py`, `checks.py`, `throttling.py`. |
| **Must not touch** | The host's settings module, the host's own apps, other apps' migrations. The app reads its configuration through `users/defaults.py` and never writes to `django.conf.settings`. |

Contracts (formal interfaces this module exposes):

| Interface | Type | Auth | Defined in |
| :--- | :--- | :--- | :--- |
| `POST /api/v1/users/register/` | REST | `AllowAny`, throttle `sensitive` (5/min) | `docs/contracts/USERS_CONTRACT.md` |
| `POST /api/v1/users/verify/` | REST | `AllowAny`, throttle `sensitive` | `docs/contracts/USERS_CONTRACT.md` |
| `GET, PATCH /api/v1/users/me/` | REST | `IsAuthenticated` | `docs/contracts/USERS_CONTRACT.md` |
| `PATCH /api/v1/users/me/profile/` | REST | `IsAuthenticated` | `docs/contracts/USERS_CONTRACT.md` |
| `PATCH /api/v1/users/me/secrets/` | REST | `IsAuthenticated` + `IsVerified` + `RequiresStepUp` | `docs/contracts/USERS_CONTRACT.md` |
| `POST /api/v1/users/me/reauth/` | REST | `IsAuthenticated`, throttle `sensitive` | `docs/contracts/USERS_CONTRACT.md` |
| `POST /api/v1/users/me/2fa/setup/` | REST | `IsAuthenticated` | `docs/contracts/USERS_CONTRACT.md` |
| `POST /api/v1/users/me/2fa/activate/` | REST | `IsAuthenticated` | `docs/contracts/USERS_CONTRACT.md` |
| `POST /api/v1/users/me/anonymize/` | REST | `IsAuthenticated` + `IsVerified` + `RequiresStepUp` | `docs/contracts/USERS_CONTRACT.md` |

Data model (summary only — full schemas belong in the contract):

- **`Address`**: reusable postal address; referenced twice by `User` (`billing_address`, `shipping_address`, both `SET_NULL`).
- **`User`** (`AbstractUser`): UUID PK, unique `email` (the `USERNAME_FIELD`), unique `username`; security telemetry (`last_ip_address`, `failed_login_attempts`, `password_changed_at`); lifecycle flags (`is_verified`, `two_factor_enabled`, `is_suspended`, `is_anonymized`, `deleted_at`). Indexed on `email` and `username`.
- **`UserProfile`** (1:1 `User`, `CASCADE`): `role` (`free`/`premium`/`admin`), locale preferences, avatar, bio, legal-consent timestamps, `registration_data` JSON, `deleted_at`.
- **`UserSecret`** (1:1 `User`, `CASCADE`): Fernet-encrypted `*_encrypted` columns paired with HMAC-SHA256 `*_index` blind-index columns for exact-match lookup (`dni`, `phone_number`); plus `date_of_birth_encrypted`, `otp_secret_key`, `otp_recovery_codes`, and `verification_otp_encrypted` / `verification_otp_expires_at`. Exchange-specific columns were removed in ADR-0005.
- **`UserSecretAudit`** (FK `User`, `CASCADE`): append-only trail of `field_affected` / `action_type` / `timestamp` / `ip_address`, ordered newest-first.

Manager layer:

| Manager | QuerySet | Visibility |
| :--- | :--- | :--- |
| `User.objects` | `SoftDeleteQuerySet` | `.alive()` by default — hides `deleted_at IS NOT NULL`. |
| `User.audit_objects` | `AuditQuerySet` | Unfiltered; `hard_delete()` raises `NotImplementedError`. |

## 4. Runtime View

**Flow 1 — Registration**
1. `POST /register/` → `UserRegistrationSerializer` validates password against `AUTH_PASSWORD_VALIDATORS` (including `PasswordComplexityValidator` from `core`) and confirms `password == password_confirm`.
2. `User.objects.create_user()` normalizes/lowercases the email and saves inside `transaction.atomic()`.
3. `post_save` receiver `create_user_profile_and_secrets` creates `UserProfile` + empty `UserSecret` atomically, and registers a `transaction.on_commit` hook for the welcome email.
4. `VerificationService.initialize_verification_flow(user)` generates a CSPRNG 6-digit OTP, stores it Fernet-encrypted in `verification_otp_encrypted` with an expiry, and returns it for out-of-band delivery. The code is never logged.
5. Response `201` with `user_id` and `email`.

**Flow 2 — Account verification**
1. `POST /verify/` with `email` + `code`.
2. `VerificationService.verify_account` rejects an expired code, compares in constant time, then sets `is_verified = True`, clears both OTP columns and appends a `UserSecretAudit` entry.

**Flow 3 — Writing a secret (step-up gated)**
1. `POST /me/reauth/` re-authenticates through `django.contrib.auth.authenticate`, so `AxesBackend` counts the attempt. On success `step_up.grant` records the timestamp in the shared cache, and in the session when one already exists (ADR-0002).
2. `PATCH /me/secrets/` passes `IsAuthenticated` + `IsVerified` + `RequiresStepUp`, which accepts either backend within `STEP_UP_WINDOW_SECONDS`.
3. `UserSecretSerializer.update` writes each supplied field from `SENSITIVE_FIELDS` (`dni`, `phone_number`, `date_of_birth`) through `set_sensitive_data()`, which Fernet-encrypts it and derives an HMAC-SHA256 blind index where the model declares one, then appends a `UserSecretAudit` row per field carrying the client IP (`HTTP_X_FORWARDED_FOR` first hop, else `REMOTE_ADDR`).

**Flow 4 — TOTP enrolment**
1. `POST /me/2fa/setup/` — rejected if `two_factor_enabled` is already true; otherwise generates a base32 secret, 8 recovery codes (stored encrypted as CSV), and returns the `otpauth://` provisioning URI.
2. `POST /me/2fa/activate/` — `verify_2fa` checks a cache key `totp_used_<user_id>_<token>` for replay, validates with `valid_window=1`, caches the token for 60 s, then sets `two_factor_enabled = True`.

**Flow 5 — GDPR anonymization**
1. `POST /me/anonymize/` requires the literal confirmation string `delete <email>`.
2. `SoftDeleteQuerySet.anonymize()` rewrites identity to `anon_<uuid>@user-app-template.internal`, sets an unusable password, wipes profile bio/avatar/marketing consent, nulls every encrypted column and blind index, then soft-deletes the row and its satellites.

## 5. Crosscutting Concepts

| Concept | Implementation |
| :--- | :--- |
| **Encryption at rest** | Fernet symmetric encryption keyed by `settings.MASTER_KEY`; `set_sensitive_data`/`get_sensitive_data` are the only sanctioned accessors. Decryption failure is logged at `CRITICAL` and returns `None`. |
| **Searchable ciphertext** | HMAC-SHA256 blind index keyed by `settings.ENCRYPTION_PEPPER`, stored alongside each encrypted column that needs exact-match lookup. |
| **Soft deletion** | `deleted_at` on `User`, `UserProfile`, `UserSecret`; propagated in one `transaction.atomic()` block. Default manager filters them out. |
| **Circular-import avoidance** | `signals.py` and `managers.py` resolve satellite models lazily via `apps.get_model()` (RA-02 `LAZY_SIGNAL_PARADIGM`). |
| **Write-only secrets** | Every sensitive serializer field is `write_only=True`, so stored values can never be read back through the API. |
| **Throttling** | `ScopedRateThrottle` with scope `sensitive` (5/minute) on `register`, `verify`, `reauth`. |

## 6. Non-negotiable Constraints

| Constraint | Verification |
| :--- | :--- |
| No PII column is stored in plaintext. | `grep -n "_encrypted" users/models/secrets.py` — every PII field ends in `_encrypted`; assert no sibling plaintext column exists. |
| Secrets are never readable through the API. | Every field in `UserSecretSerializer` declares `write_only=True`. |
| Anonymization is irreversible. | `SoftDeleteQuerySet.restore()` filters `is_anonymized=False`, so anonymized rows can never be restored. |
| Audit history cannot be physically deleted. | `AuditQuerySet.hard_delete()` raises `NotImplementedError`. |
| A TOTP token cannot be replayed inside its window, across workers. | Cache key `totp_used_<user_id>_<token>` set for 60 s, on the shared backend required by ADR-0001. |
| Credentials must come from a CSPRNG, never `random`. | `test_verification.py::test_generator_does_not_use_the_random_module`. |
| A verification code expires. | `verification_otp_expires_at` is enforced in `verify_account`. |
| Step-up gated endpoints must be reachable by both client styles. | `test_step_up.py` covers session and bearer-token paths. |
| The admin must never render a stored secret value. | `UserSecretInline.fields` is an allow-list of derived indicators; `test_admin_does_not_render_secret_ciphertext`. |
| Satellite models always exist for a live user. | `post_save` receiver runs inside `transaction.atomic()`; failure rolls the user creation back. |
| `MASTER_KEY` and `ENCRYPTION_PEPPER` must be present at boot. | `users/encryption.py` raises `ImproperlyConfigured` when either is unset; the host declares them (`docs/contracts/USERS_CONTRACT.md`, *Host requirements*). |

## 7. Decisions

This module's ADR log — link, don't restate:

- `docs/decisions/ADR-0002-hybrid-step-up-authentication.md`: step-up resolves through the session and a shared-cache grant, so token clients can reach gated endpoints.
- `docs/decisions/ADR-0004-dedicated-encrypted-otp-storage.md`: the verification code has its own encrypted column, with an expiry.
- `docs/decisions/ADR-0005-generic-secret-vault.md`: exchange-specific columns removed; the vault and its endpoint serve generic identity data.

Still undocumented, inherited (retroactive candidates, `§3.1` triggers in brackets):

- _(pending)_ Fernet + HMAC blind index for searchable encrypted PII — trigger #3.
- _(pending)_ Soft deletion plus irreversible anonymization as the GDPR strategy — triggers #1 and #3.
- _(pending)_ Email as `USERNAME_FIELD` with UUID primary key — trigger #2.

## 8. Glossary

| Term | Meaning in this module |
| :--- | :--- |
| **Blind index** | HMAC-SHA256 digest of a plaintext value, stored beside the ciphertext so exact-match queries work without decryption. |
| **Step-Up Auth** | A re-authentication proving password possession within the last 5 minutes, required before secrets or anonymization. |
| **Satellite model** | `UserProfile` / `UserSecret` — 1:1 records auto-created by the `post_save` signal and lifecycle-bound to their `User`. |
| **Soft delete** | Setting `deleted_at`; no SQL `DELETE` is issued, and the row stays reachable through `audit_objects`. |
| **Anonymization** | Destructive, irreversible PII erasure that keeps the row for referential integrity. |

---
*A module without a ratified Blueprint cannot enter Execution (agents.md §0). C4 Level 3 (Component diagram) required here if this module qualifies per `rules/documentation_standard.md §2.1` — `users` is the qualifying container of the `backend` stack, currently in advisory mode (bootstrap).*
