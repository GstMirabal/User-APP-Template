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
| `200` | Identity rewritten, every encrypted column nulled, row soft-deleted. |
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

Optional, with defaults: `STEP_UP_WINDOW_SECONDS` (300), `VERIFICATION_OTP_TTL_MINUTES` (15).
