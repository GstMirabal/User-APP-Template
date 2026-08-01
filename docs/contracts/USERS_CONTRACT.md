# 📄 Contract: USERS
**File**: `docs/contracts/USERS_CONTRACT.md` (RA-06 Option B naming)
**Module**: USERS
**Last Audit Sprint**: #004
**Last Audit Date**: 2026-08-01

---

The REST surface this app exposes, mounted wherever the host project includes `users.urls` — `api/v1/users/` in the examples below. Reference material: shapes and status codes, no rationale. The reasoning behind each control lives in the ADRs linked from `docs/architecture/USERS_BLUEPRINT.md`.

Authentication is whatever the host project configures. Both session and bearer-token clients are supported on every authenticated endpoint, including the step-up gated ones ([ADR-0002](../decisions/ADR-0002-hybrid-step-up-authentication.md)).

## Permission vocabulary

| Gate | Meaning |
| :--- | :--- |
| `AllowAny` | No authentication. |
| `IsAuthenticated` | A valid session or bearer token. |
| `IsVerified` | The account completed email verification (`user.is_verified`). |
| `RequiresStepUp` | The caller re-entered their password within `STEP_UP_WINDOW_SECONDS` (default 300). |

`sensitive` throttle scope: 5 requests per minute.

---

## `POST register/`

Creates an account and issues a verification code.

**Auth**: `AllowAny` · **Throttle**: `sensitive`

| Field | Type | Required |
| :--- | :--- | :--- |
| `email` | string | yes — unique, becomes the login identifier |
| `username` | string | yes — unique |
| `password` | string | yes — validated against the host's `AUTH_PASSWORD_VALIDATORS` |
| `password_confirm` | string | yes — must equal `password` |
| `language_code` | string | no — defaults to `en-us` |

| Status | Body |
| :--- | :--- |
| `201` | `{"detail": "...", "user_id": "<uuid>", "email": "..."}` |
| `400` | Field errors. `password_confirm` mismatch reports under that key. |

Creating a user also provisions its `UserProfile` and `UserSecret` atomically, via a `post_save` receiver. A failure there rolls the user creation back.

The verification code is **announced, not delivered**: `verification_code_issued` fires with the plaintext, and the host sends it. See *Host requirements* below.

## `POST verify/`

Consumes a verification code.

**Auth**: `AllowAny` · **Throttle**: `sensitive`

| Field | Type |
| :--- | :--- |
| `email` | string |
| `code` | string |

| Status | Meaning |
| :--- | :--- |
| `200` | Verified. `is_verified` becomes true and both code columns are cleared. |
| `400` | Missing field, wrong code, or **expired** code — the response does not distinguish, deliberately. |
| `404` | No such user. |

Codes expire after `VERIFICATION_OTP_TTL_MINUTES` (default 15). Comparison is constant-time. Success appends a `UserSecretAudit` row.

## `GET, PATCH me/`

Reads or updates the caller's own core record.

**Auth**: `IsAuthenticated`

Readable: `id`, `email`, `username`, `is_verified`, `profile`, `failed_login_attempts`, `date_joined`. Of those, `id`, `is_verified`, `failed_login_attempts` and `date_joined` are read-only.

| Status | Body |
| :--- | :--- |
| `200` | The serialized user. |
| `400` | Validation errors on `PATCH`. |

## `PATCH me/profile/`

Updates preferences and presentation data.

**Auth**: `IsAuthenticated`

Writable: `timezone`, `preferred_currency`, `language_code`, `avatar`, `bio`, `email_notifications_enabled`. `role` is exposed read-only — a user cannot promote themselves.

## `POST me/reauth/`

Proves password possession and opens the step-up window.

**Auth**: `IsAuthenticated` · **Throttle**: `sensitive`

| Field | Type |
| :--- | :--- |
| `password` | string |

| Status | Meaning |
| :--- | :--- |
| `200` | Step-up granted for `STEP_UP_WINDOW_SECONDS`. |
| `400` | No password supplied — a client error, not a failed credential. |
| `403` | Wrong password. |

Re-authentication goes through the host's authentication backend, so a lockout backend such as `django-axes` counts failed attempts here as it does on login.

## `PATCH me/secrets/`

Writes identity data into the encrypted vault.

**Auth**: `IsAuthenticated` + `IsVerified` + `RequiresStepUp`

| Field | Type | Notes |
| :--- | :--- | :--- |
| `dni` | string | Encrypted, blind-indexed, unique |
| `phone_number` | string | Encrypted, blind-indexed |
| `date_of_birth` | date (`YYYY-MM-DD`) | Encrypted |

At least one field is required. **Every field is write-only**: a stored value can be overwritten but never read back through the API, and the response echoes nothing. Each written field appends a `UserSecretAudit` row carrying the client IP.

| Status | Meaning |
| :--- | :--- |
| `200` | `{"detail": "Sensitive data stored, encrypted at rest."}` |
| `400` | No known field supplied. |
| `403` | Not verified, or no valid step-up. |

## `POST me/2fa/setup/`

Begins TOTP enrolment.

**Auth**: `IsAuthenticated`

| Status | Body |
| :--- | :--- |
| `200` | `{"detail": "...", "otp_uri": "otpauth://...", "secret": "...", "recovery_codes": [8 strings]}` |
| `400` | Two-factor is already active — deactivate before reconfiguring. |

The recovery codes are returned **once**. They are stored encrypted and never retrievable again.

## `POST me/2fa/activate/`

Confirms enrolment with a live token.

**Auth**: `IsAuthenticated`

| Field | Type |
| :--- | :--- |
| `token` | string — 6 digits |

| Status | Meaning |
| :--- | :--- |
| `200` | `two_factor_enabled` becomes true. |
| `400` | Missing, invalid, expired, or **already used** token. |

Accepts a ±1 time-step drift. A token accepted once is refused for 60 seconds afterwards, which requires a cache shared across workers — see *Host requirements*.

## `POST me/anonymize/`

Irreversibly anonymises the account.

**Auth**: `IsAuthenticated` + `IsVerified` + `RequiresStepUp`

| Field | Type |
| :--- | :--- |
| `confirmation` | string — must equal `delete <the caller's email>` |

| Status | Meaning |
| :--- | :--- |
| `200` | Identity rewritten, every encrypted column nulled, profile metadata cleared, row soft-deleted. |
| `403` | Confirmation string did not match, or no valid step-up. |

**This cannot be undone.** `restore()` explicitly refuses anonymised rows.

---

## Host requirements

The app is not self-contained. A host project must provide:

| Requirement | Why |
| :--- | :--- |
| `AUTH_USER_MODEL = "users.User"` | The app ships a custom user model, so it cannot be added to a project with existing auth data. |
| `MASTER_KEY`, `ENCRYPTION_PEPPER` | Fernet encryption and blind indexing of every stored secret. |
| **A cache shared across workers** | TOTP anti-replay and step-up grants. On a per-process backend both silently fail under more than one worker — the request lands on a worker that never saw the earlier state. |
| `users.urls` included | Nothing is routed otherwise. |
| `AXES_USERNAME_FORM_FIELD = "username"` | This app logs in by email, and `django-axes` 8 defaults this to the model's `USERNAME_FIELD`. Django's own login form (`/admin/login/`, `LoginView`) names its field `username` regardless, so axes finds no matching key and stores every failed attempt as `username=None` — lockout degrades from per-account to per-IP and `AXES_RESET_ON_SUCCESS` stops matching. No exception is raised. |
| **A receiver for `verification_code_issued`** | The app issues verification codes and does not deliver them. Without a receiver, registration succeeds and the account can never be verified: the stored column is encrypted and never read back, so the signal carries the only readable copy. |

Both of the last two are checked at startup — `manage.py check` reports `users.W001` and `users.W002` — because neither raises an exception on its own.

### Logging

The app writes to loggers named after its modules (`users.views`, `users.services`, and so on) and configures nothing. Under Django's defaults those records reach no handler, so a host that registers neither a `users` logger nor a root handler discards all of the following:

| Record | Level | Meaning |
| :--- | :--- | :--- |
| Decryption failed — possible `MASTER_KEY` mismatch | `critical` | Stored personal data has become unreadable. The single most important alarm this app raises. |
| TOTP replay attempt | `warning` | A one-time code was presented twice — an active attack indicator. |
| Failed step-up re-authentication | `warning` | Password guessing against an authenticated session. |
| Irreversible anonymisation started | `warning` | The audit trail for an action that cannot be undone. |
| Invalid or expired verification code | `warning` / `info` | Registration-flow abuse. |

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"users": {"handlers": ["console"], "level": "INFO"}},
}
```

This is not enforced by a system check. A host may route these through the root logger instead, and a warning that fires on a correct configuration teaches people to ignore warnings.

### Delivering the verification code

```python
from django.core.mail import send_mail
from django.dispatch import receiver

from users.events import verification_code_issued


@receiver(verification_code_issued)
def deliver_verification_code(sender, user, code, expires_at, **kwargs):
    send_mail(
        subject="Verify your account",
        message=f"Your code is {code}. It expires at {expires_at:%H:%M UTC}.",
        from_email=None,
        recipient_list=[user.email],
    )
```

Email is one option. The signal exists because this app cannot know whether a
given project reaches its users by mail, SMS, push or a provider API, and
picking one would impose a template, a subject line and a set of `EMAIL_*`
settings on every consumer.

Optional, with defaults: `STEP_UP_WINDOW_SECONDS` (300), `VERIFICATION_OTP_TTL_MINUTES` (15).

### Strongly recommended

| Setting | Why |
| :--- | :--- |
| `SIMPLE_JWT["SIGNING_KEY"]` set to a value of its own, not `SECRET_KEY` | HS256 is symmetric, so the verification key and the signing key are the same bytes: disclosure of `SECRET_KEY` becomes the ability to mint a token for any user id. The two also rotate differently — rotating `SECRET_KEY` drops sessions and reset links, rotating the JWT key drops every outstanding token for every API client. Sharing one value forces both consequences whenever either is needed. Full reasoning in [ADR-0003](../decisions/ADR-0003-separate-jwt-signing-key.md). |

### Generating the required keys

`MASTER_KEY` must be a valid Fernet key and `ENCRYPTION_PEPPER` a high-entropy
value; neither is something to invent by hand.

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # MASTER_KEY
python -c "import secrets; print(secrets.token_hex(32))"                                    # ENCRYPTION_PEPPER
python -c "import secrets; print(secrets.token_urlsafe(64))"                                # SIMPLE_JWT signing key
```

**Rotating `MASTER_KEY` or `ENCRYPTION_PEPPER` after data exists makes the
stored secrets unreadable.** Ciphertext is decryptable only with the key that
wrote it, and a blind index is only searchable under the pepper that built it.
Neither is re-derivable from the stored value, so rotation means re-encrypting
and re-indexing every row while the old values are still available.
