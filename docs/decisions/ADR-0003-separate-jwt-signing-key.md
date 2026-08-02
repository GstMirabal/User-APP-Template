# 📜 ADR-0003: Separate JWT signing key from SECRET_KEY
**Status**: `Superseded` (Sprint #004)
**Date**: 2026-07-30
**Triggers**: 3 (`rules/documentation_standard.md §3.1`)

---

> [!NOTE]
> **Superseded, not reversed.** Sprint #004 reduced this repository to an
> installable app, and the settings this decision changed —
> `SIMPLE_JWT["SIGNING_KEY"]`, `config.toml`, `generate_secrets.py` — went with
> the scaffolding. Nothing here configures JWT any more, so the decision no
> longer has anything to bind to in this codebase.
>
> The reasoning still holds for anyone installing this app, and is why
> `JWT_SIGNING_KEY` appears under *Host requirements* in
> [`USERS_CONTRACT.md`](../contracts/USERS_CONTRACT.md). Read the record below
> for why the two keys should not be shared; read the contract for what to set.

## 1. Context

`SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY`.

Django's `SECRET_KEY` signs session cookies, CSRF tokens, password-reset links and any `signing.dumps()` payload. It is a long-lived value that appears in settings dumps, is copied between environments during setup, and is the first thing a `DEBUG=True` traceback exposes — a page this project could until recently reach in production, since `DEBUG=False` was inert (see Sprint #001 defect B5).

With the keys shared, disclosure of `SECRET_KEY` is simultaneously the ability to mint arbitrary access tokens for any user id, because the algorithm is symmetric HS256: the verification key and the signing key are the same bytes.

The two keys also have incompatible rotation profiles. Rotating `SECRET_KEY` invalidates sessions and password-reset links, which is tolerable during a maintenance window. Rotating the JWT signing key invalidates every outstanding access and refresh token for every API client. Sharing one value forces both consequences whenever either is needed.

## 2. Decision

Introduce a dedicated `JWT_SIGNING_KEY`, resolved from `config.toml` with an environment fallback, and use it for `SIMPLE_JWT["SIGNING_KEY"]`.

When it is absent, fall back to `SECRET_KEY` and emit a warning rather than failing to boot. An existing deployment that upgrades this template must not be locked out by a new mandatory setting, and the fallback reproduces exactly the previous behaviour.

The scaffolding's secret generator emitted the new key alongside the others, and `config.toml.example` carried the placeholder. Both left with the scaffolding in Sprint #004; see the note above.

## 3. Consequences

**Easier.** The two keys rotate independently. Disclosure of one no longer implies the other. The signing key can be held in a narrower scope than the settings-wide `SECRET_KEY`.

**Harder.** One more secret to provision, store and rotate. A deployment that sets `JWT_SIGNING_KEY` for the first time invalidates all outstanding tokens at that moment — clients re-authenticate once. That is a deliberate, announced cost rather than a silent one.

The fallback is a real weakness: a deployment that never sets the key stays exactly as exposed as before, and only a log warning distinguishes the two states. Making it mandatory would have been stronger, and was rejected only because a template that refuses to boot after an upgrade gets pinned to the old version instead of fixed. The warning is emitted at startup, not buried at `DEBUG` level, so it is visible in the same logs Sprint #001 made functional.

This does not address the more fundamental property that HS256 is symmetric: any service that must *verify* tokens must hold the key that *mints* them. A move to RS256 with a public verification key is the natural next step for a deployment with more than one service, and warrants its own ADR.

## 4. Deciders

Repository owner, on the recommendation of the Sprint #000 audit.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **Dedicated `JWT_SIGNING_KEY`, falling back to `SECRET_KEY` with a warning** (chosen) | Independent rotation; no forced re-auth on upgrade; blast radius separated for anyone who sets it | Fallback leaves non-adopters exactly as exposed; two keys to manage |
| Dedicated key, mandatory | Strictly stronger; no silent weak state | Existing deployments fail to boot on upgrade; encourages pinning the old version |
| Switch to RS256 with a key pair | Verifiers hold only the public key; correct for multi-service topologies | Key generation and distribution is real operational work for a single-service template; larger change than the defect requires |
| Leave as is | No work | A single disclosure yields both session forgery and token forgery |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`).*
