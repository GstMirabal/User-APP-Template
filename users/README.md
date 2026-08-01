# `users`

Identity and access management for Django: accounts, credentials, two-factor
authentication and encrypted personal data.

This file travels with the package. If you are reading it inside a vendored
copy, the full documentation lives at
[GstMirabal/django-users-app](https://github.com/GstMirabal/django-users-app).

## What is in here

| Module | Holds |
| :--- | :--- |
| `models/` | `User` (email login, UUID primary key), `UserProfile`, `UserSecret`, `UserSecretAudit` |
| `serializers/` | Request and response shapes for the nine endpoints |
| `views.py` | The viewset behind `users.urls` |
| `services.py` | Verification codes and TOTP enrolment |
| `encryption.py` | Fernet encryption and HMAC blind indexing |
| `step_up.py` | Re-authentication grants, held in the cache and the session |
| `permissions.py` | `IsVerified` and `RequiresStepUp` |
| `defaults.py` | Settings this app reads, and the fallbacks it applies |
| `events.py` | Signals the app emits for a host to act on |
| `checks.py` | Startup checks for host configuration the app cannot supply |

## Installing it

```python
INSTALLED_APPS = [..., "rest_framework", "rest_framework_simplejwt",
                  "rest_framework_simplejwt.token_blacklist", "axes", "users"]
AUTH_USER_MODEL = "users.User"
```

```python
urlpatterns = [path("api/v1/users/", include("users.urls"))]
```

> [!IMPORTANT]
> `AUTH_USER_MODEL` can only be set before a project's first migration, so this
> app goes into a **new** project. It cannot be added to one that already has
> auth data.

Five things must come from the host: `MASTER_KEY`, `ENCRYPTION_PEPPER`, a cache
shared across workers, `AXES_USERNAME_FORM_FIELD = "username"`, and a receiver
for `verification_code_issued`. The last two report as `users.W002` and
`users.W001` under `manage.py check`, because neither raises on its own —
missing them costs you per-account lockout and account verification
respectively, in silence.

Each is explained, with the reason it cannot be defaulted, in
[`USERS_CONTRACT.md`](../docs/contracts/USERS_CONTRACT.md).

## What the vault stores

`UserSecret` holds `dni`, `phone_number` and `date_of_birth`. They are encrypted
at rest with Fernet — symmetric AES-CBC with an HMAC, not a key pair — and
blind-indexed so exact-match lookup still works without decrypting a column.

Every field is **write-only through the API**: a stored value can be replaced
but never read back, and the response echoes nothing. Each write appends a
`UserSecretAudit` row carrying the client address. Writing requires a verified
account and a re-authentication within the step-up window.

## Security features

* **JWT authentication** — stateless sessions with rotating refresh tokens and
  a blacklist.
* **TOTP two-factor** — compatible with any authenticator app, with recovery
  codes issued once and anti-replay that holds across workers.
* **Step-up authentication** — sensitive writes and irreversible deletion
  require a recent password re-entry, for session and bearer-token clients.
* **Brute-force protection** — `django-axes` lockout covering `/me/reauth/` as
  well as login.
* **Role-based access** — `role` on the profile is read-only through the API, so
  an account cannot promote itself.
* **Restrained admin** — the inline for encrypted fields is an allow-list, so a
  new encrypted column is not exposed to the admin DOM by default.
* **GDPR anonymisation** — irreversible erasure layered on soft deletion.
  `restore()` refuses an anonymised row.
