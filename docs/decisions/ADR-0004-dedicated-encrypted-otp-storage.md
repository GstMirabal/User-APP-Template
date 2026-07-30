# 📜 ADR-0004: Dedicated encrypted storage for the verification OTP
**Status**: `Accepted`
**Date**: 2026-07-30
**Triggers**: 1, 3 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

`VerificationService.initialize_verification_flow` stored the registration one-time password like this:

```python
user.secrets.api_key_binance_encrypted = f"OTP_PENDING:{otp}"
```

Four distinct problems in one line, all verified in the Sprint #000 audit:

- **Wrong column.** `api_key_binance_encrypted` holds a user's exchange API key. Registering — or re-triggering verification for — a user overwrites a credential they supplied, and `verify_account` then blanks it entirely.
- **Plaintext in an `_encrypted` column.** The assignment bypasses `UserSecret.set_sensitive_data()`, so the value is written raw into a column whose name asserts otherwise. Every other sensitive value in the model goes through Fernet.
- **No expiry.** An OTP written at registration stays valid indefinitely.
- **Logged in clear.** `logger.info("--- [MOCK OTP SENT]: %s ---", otp)` writes the code to the log stream. This was inert only because application logs reached no handler at all — a Sprint #001 defect (B4). Repairing logging turned a latent leak into a live one.

The coupling had reached the tests: `test_user_verification_flow` reads the OTP back out of `api_key_binance_encrypted`.

## 2. Decision

Give the OTP its own storage on `UserSecret`:

- `verification_otp_encrypted` — written through `set_sensitive_data()`, so it is Fernet-encrypted like every other sensitive field.
- `verification_otp_expires_at` — a timestamp, with the lifetime configurable via `VERIFICATION_OTP_TTL_MINUTES`.

`verify_account` rejects an expired code and clears both fields on success. Verification events are recorded in `UserSecretAudit`, which already exists for exactly this purpose.

The `logger.info` carrying the code drops to `DEBUG` and no longer includes the OTP value; the log line records that a code was issued, not what it was.

The Binance columns are left in place by this ADR. Removing them is a separate destructive migration scheduled for Sprint #003, and conflating the two would make this change harder to review and to roll back.

## 3. Consequences

**Easier.** Registering a user no longer destroys their stored exchange credential. The OTP is encrypted at rest like every other secret. Codes expire. The audit trail covers verification. The OTP stops appearing in logs.

**Harder.** A migration adding two columns, and a second one in Sprint #003 removing the Binance columns — two schema changes where a single combined one was possible. That is the deliberate cost of keeping a security fix separable from a destructive cleanup.

Expiry introduces a failure mode that did not exist: a user who waits too long must request a new code, and no resend endpoint exists yet. Until one is added, the recovery path for an expired OTP is an administrator re-triggering verification. This is tracked as follow-up work rather than fixed here, because a resend endpoint needs its own rate limiting and is not a prerequisite for closing the leak.

Any user registered before this migration holds an OTP in the old location. Those rows are not migrated: the values are unverifiable plaintext markers with no expiry, and carrying them forward would import the defect into the new column. Affected users re-verify.

## 4. Deciders

Repository owner, who additionally chose to generalise the vault away from exchange-specific columns in Sprint #003.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **Dedicated encrypted field + expiry timestamp** (chosen) | Fixes all four defects; reuses the existing `set_sensitive_data` accessor and `UserSecretAudit`; separable from the Binance removal | Two migrations instead of one; no resend path for expired codes yet |
| Store the OTP in the cache with a native TTL | No migration; expiry for free | Verification state disappears on cache eviction or Redis restart; a user mid-registration is stranded with no server-side record |
| Store only a hash of the OTP | Never recoverable, even by an operator | A six-digit code has a trivial search space; a hash adds little over the Fernet encryption already available, and blocks operator-assisted support |
| Keep the field, just encrypt it | Smallest diff | Leaves the credential-overwrite bug, the worst of the four |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`).*
