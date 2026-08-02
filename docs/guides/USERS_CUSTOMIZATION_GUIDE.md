# How to strip this template down to what you need

**Last Audit Sprint**: #003
**Last Audit Date**: 2026-07-30
**Last Audit Commit SHA**: 99c15c8

---

This template ships a complete user-management system. Some of it is the identity core, and some is opinionated product surface you may not want. Removing what you don't need is easy; rebuilding what you do need is not — which is why nothing here has been pre-emptively removed for you.

This guide says which is which, and what breaks when you pull each thread.

## Goal

Reduce the template to the subset your project actually needs, without silently disabling a security control.

## Prerequisites

- A working checkout: `make db-up && make migrate && make test` (85 tests should pass).
- You have not yet run this in production. Every removal below is a destructive migration.

---

## 1. The identity core — do not remove

Removing any of this breaks authentication, the encryption path, or a legal obligation. If you find yourself wanting to, you probably want a different template.

| Component | Where | Why it is core |
| :--- | :--- | :--- |
| `User` model | `models/user.py` | UUID primary key, email as `USERNAME_FIELD`. Everything references it. |
| `CustomUserManager` / `SoftDeleteQuerySet` | `managers.py` | Soft deletion, restore, anonymisation. The default manager hides deleted rows. |
| `AuditManager` | `managers.py` | The only way to reach deleted records; refuses physical deletion. |
| `UserSecret` + `utils/encryption.py` | `models/secrets.py` | Fernet encryption and HMAC blind indexes. `set_sensitive_data` / `get_sensitive_data` are the only sanctioned accessors. |
| `UserSecretAudit` | `models/secrets.py` | Append-only trail of secret writes. |
| `step_up.py` + `RequiresStepUp` | `step_up.py`, `permissions.py` | Guards secret writes and irreversible anonymisation ([ADR-0002](../decisions/ADR-0002-hybrid-step-up-authentication.md)). |
| Verification OTP fields | `models/secrets.py` | Encrypted, with expiry ([ADR-0004](../decisions/ADR-0004-dedicated-encrypted-otp-storage.md)). |
| `PasswordComplexityValidator` | `apps/core/validators.py` | Server-side password policy. |
| `apps/core/checks.py` | `apps/core/checks.py` | Catches admin misconfiguration at startup; a real defect shipped past Django's own checks. |
| Cache configuration | `config/settings/cache.py` | Not an optimisation. TOTP anti-replay and step-up both depend on shared state ([ADR-0001](../decisions/ADR-0001-shared-cache-backend.md)). |

---

## 2. Optional extras — safe to remove

Each row is independent. Work top to bottom; the later ones assume the earlier ones are still present.

### 2.1 Postal addresses

**Remove**: the `Address` model and the `billing_address` / `shipping_address` foreign keys on `User`.

**Breaks**: nothing else. Both keys are nullable with `on_delete=SET_NULL` and no code reads them.

```bash
# after deleting the model and the two fields from models/user.py
python manage.py makemigrations users && python manage.py migrate
```

### 2.2 Profile presentation fields

**Remove**: `avatar`, `bio` from `UserProfile`.

**Breaks**: `UserProfileSerializer.Meta.fields` lists both — remove them there too, or `PATCH /me/profile/` raises at import. `avatar` is the only reason `MEDIA_ROOT` / `MEDIA_URL` exist; drop those from `config/settings/base.py` if nothing else uses them.

### 2.3 Roles (free / premium / admin)

**Remove**: `UserProfile.UserRole`, the `role` field, and `IsPremiumUser` in `permissions.py`.

**Breaks**: `UserAdmin.list_filter` references `profile__role` and `get_role`; `UserProfileSerializer` exposes `role` as read-only. Remove all three. Nothing else consumes roles — `IsPremiumUser` is not applied to any endpoint, so it is dead code you are simply deleting.

**Keep instead if**: you want tiering later. The field costs one column.

### 2.4 Marketing consent

**Remove**: `UserProfile.marketing_consent`.

**Breaks**: `SoftDeleteQuerySet.anonymize` sets it to `False` — remove that line, or anonymisation raises `AttributeError`.

**Think first**: if you send any marketing email, this field is likely a legal requirement in your jurisdiction, not a preference.

### 2.5 Currency preference

**Remove**: `UserProfile.preferred_currency`.

**Breaks**: `UserProfileSerializer.Meta.fields` and `UserProfileInline.fields` in the admin.

**Note**: this was flagged as crypto residue during the original audit and that judgement was wrong. It is an ordinary preference alongside `timezone` and `language_code`, and it stays in the template for that reason.

### 2.6 National ID / date of birth

**Remove**: `dni_encrypted`, `dni_index`, `date_of_birth_encrypted` from `UserSecret`.

**Breaks**: `SENSITIVE_FIELDS` in `serializers/secrets.py`, the `has_identity_data` admin indicator, and `SoftDeleteQuerySet.anonymize`. Note that `dni_index` carries a `unique=True` constraint — dropping it also drops that guarantee.

**Think first**: if you remove all three plus phone number, `PATCH /me/secrets/` has nothing left to write and the step-up machinery guards an empty endpoint. Remove the endpoint too, or give it your own sensitive fields.

### 2.7 Two-factor authentication

**Remove**: `otp_secret_key`, `otp_recovery_codes`, `User.two_factor_enabled`, the `setup_2fa` / `activate_2fa` actions, and `pyotp` from `requirements.txt`.

**Breaks**: `VerificationService.setup_2fa` and `verify_2fa`, the `has_two_factor` admin indicator, `UserAdmin` fieldsets, and `anonymize`.

**Think first**: this is the single largest security feature in the template. Removing it to reduce surface area is a real trade, not a cleanup.

---

## 3. Things that look optional but are not

| Looks removable | Actually |
| :--- | :--- |
| `phone_verified_at` | Never written by any code path, but displayed in the admin secret inline and the only place a phone-verification flow would record its result. Costs one nullable column. |
| `registration_data` JSON field | Populated by the `post_save` receiver from `_registration_metadata`. Removing it means editing `signals.py` too. |
| `failed_login_attempts` on `User` | Never written — `django-axes` keeps its own counters — but read by `UserSerializer` and shown read-only in the admin. Remove all three references together or leave them. |
| The `sensitive` throttle scope | Applied to registration, verification and re-authentication. It is the second layer under Axes on the re-auth endpoint. |

---

## 4. Verify it worked

After any removal:

```bash
python manage.py makemigrations users
python manage.py migrate
python manage.py check --fail-level WARNING   # includes users.W001 and users.W002
pytest -q
```

The admin-integrity check (`core.E001`) catches the most common mistake here: deleting a model field while leaving its name in a `ModelAdmin` or inline `fields` list. Django's own checks do not catch that, and the page fails with a 500 at request time instead.

## 5. If something goes wrong

| Symptom | Cause |
| :--- | :--- |
| `FieldError: Unknown field(s) (x) specified for Y` | A removed field is still named in an admin `fields`/`fieldsets` or a serializer's `Meta.fields`. |
| `AttributeError` during anonymisation | `SoftDeleteQuerySet.anonymize` still clears a field you removed. |
| Tests fail in `test_secrets.py` | You removed a field from `SENSITIVE_FIELDS` but not from the test, or vice versa. |
| `ImproperlyConfigured` about the cache | Unrelated to your removal — set `REDIS_URL` in `config.toml`, required whenever `DEBUG` is false. |

---
*Reference for what each module currently contains: `docs/architecture/USERS_BLUEPRINT.md`.*
