# 📜 ADR-0005: Generic secret vault, without exchange-specific columns
**Status**: `Accepted`
**Date**: 2026-07-30
**Triggers**: 1, 2, 3 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

`UserSecret` carries three columns inherited from the cryptocurrency trading project this template was extracted from:

- `api_key_binance_encrypted`
- `api_key_binance_index`
- `api_secret_binance_encrypted`

They are the only fields `UserSecretSerializer` exposes, so `PATCH /me/secrets/` — the endpoint guarded by verification plus step-up re-authentication (ADR-0002), the most heavily protected write in the project — exists solely to store credentials for one named exchange.

The repository is published as a generic Django user-management template. A consumer building a SaaS, a marketplace or an internal tool inherits a schema naming a crypto exchange, a serializer that accepts only its credentials, and an anonymisation routine that clears them by name.

The same columns already caused a defect: the registration OTP was stored in `api_key_binance_encrypted`, so issuing a verification code destroyed a user's stored key (ADR-0004). That was fixed by giving the OTP its own field; the columns themselves remained, deliberately, so a security fix would not be entangled with a destructive cleanup.

Meanwhile the vault already holds genuinely generic identity data — `dni`, `phone_number`, `date_of_birth` — encrypted with blind indexes, which no endpoint exposes at all.

## 2. Decision

Drop the three exchange-specific columns.

Repoint `UserSecretSerializer` at the identity fields the vault already holds: `dni`, `phone_number` and `date_of_birth`, all write-only and routed through `set_sensitive_data()` so they are Fernet-encrypted and blind-indexed exactly as before. `PATCH /me/secrets/` keeps its meaning — submitting sensitive personal data behind step-up — without naming a third party.

`preferred_currency` on `UserProfile` stays. It was flagged as crypto residue during the audit and that was wrong: a currency preference sits alongside `timezone` and `language_code` as an ordinary user setting in any commerce-adjacent application.

A consumer needing third-party credentials adds their own columns or a dedicated model. The template should not presume which provider.

## 3. Consequences

**Easier.** The schema no longer names a company unrelated to the template's purpose. `/me/secrets/` becomes useful to every consumer rather than to one. The identity fields become reachable through the API for the first time.

**Harder.** This is an irreversible migration: any deployment holding real exchange credentials in those columns loses them. That is the correct call for a template whose consumers do not have such data, and the wrong one for the original project it came from — which is why this lands as its own ADR and its own migration, announced rather than folded into a refactor. A deployment that does hold such data should not apply this migration without first exporting those columns.

The audit trail keeps historical `UserSecretAudit` rows whose `field_affected` reads `api_key_binance`. Those are not rewritten: they are an accurate record of an event that happened, and rewriting history to match a new schema would be worse than a stale label.

Removing the columns also removes the only blind-indexed field that was exercised by a serializer, so the blind-index path is now reached through `dni` and `phone_number` instead. Both already had index columns; no schema change is needed for that.

## 4. Deciders

Repository owner, who chose "remove and generalise" over a generic key/value credential model when the option was put.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **Drop the columns; repoint the serializer at the identity fields** (chosen) | Schema stops naming a third party; the protected endpoint gains a purpose every consumer shares; identity fields become reachable | Irreversible for anyone holding real credentials there |
| Generic `ThirdPartyCredential` model (provider, key, secret), encrypted | Any provider supported; extensible | Builds a feature nobody has asked for into a template; more surface to secure and to document |
| Rename the columns to `api_key_external_*` | Smallest change; no data loss | Keeps a credential-shaped field with no consumer, and pretends generality the code does not have |
| Keep them | No work | The template ships a crypto exchange in its schema |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`).*
