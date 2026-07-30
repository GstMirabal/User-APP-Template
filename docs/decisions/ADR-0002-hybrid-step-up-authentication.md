# 📜 ADR-0002: Hybrid step-up authentication
**Status**: `Accepted`
**Date**: 2026-07-30
**Triggers**: 2, 3 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

`RequiresStepUp` gates the two most destructive endpoints in the project: `PATCH /me/secrets/`, which writes encrypted PII and exchange credentials, and `POST /me/anonymize/`, which is irreversible. It requires the caller to have re-entered their password within the last five minutes.

That re-authentication timestamp is stored in `request.session`, written by `POST /me/reauth/`. But `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` accepts both `SessionAuthentication` and `JWTAuthentication`, and the project ships SimpleJWT token endpoints, `drf-spectacular` schemas, Swagger and Redoc — it is positioned as an API-first template.

A client authenticating with a bearer token has no session. `request.session` exists (the middleware is installed) but is empty and is never persisted, because nothing sets a session cookie on that request path. `step_up_timestamp` is therefore always absent, `RequiresStepUp.has_permission` always returns `False`, and both endpoints are permanently unreachable. The existing tests did not catch this: they use `client.force_login`, which establishes a session.

So the template's own primary authentication mechanism cannot reach its own most-protected endpoints.

## 2. Decision

`RequiresStepUp` resolves through two backends, in order:

1. If `request.session` carries a valid, unexpired `step_up_timestamp`, grant.
2. Otherwise, look up a cache key `step_up:<user_id>` written with a TTL equal to the step-up window.

`POST /me/reauth/` writes both on success. Session clients keep working exactly as before; token clients now work at all.

The five-minute window moves from a hardcoded `timedelta` inside the permission class to a `STEP_UP_WINDOW_SECONDS` setting.

The cache path depends on the shared Redis backend from ADR-0001. With a per-process cache it would be no better than the session for a multi-worker deployment.

## 3. Consequences

**Easier.** JWT clients can reach `/me/secrets/` and `/me/anonymize/`. The window becomes configurable per deployment rather than per code edit. Both paths share one expiry rule instead of drifting.

**Harder.** Step-up state now lives in two places, and "revoke this user's step-up" means clearing both. Server-side step-up state is also a new thing to reason about: unlike the session, the cache entry survives the client discarding its token, so a stolen token replayed within the window inherits the step-up grant. The window is short and re-authentication is password-gated, but this is a genuine widening compared to session-only, and the reason the window stays at five minutes rather than being lengthened for convenience.

Keying on user id alone means step-up granted in one client grants it in every concurrent session of that user. Keying on a token identifier instead would scope it tighter; that is rejected here only because it does not work for the session path, and a single mechanism spanning both was the point. If per-device scoping becomes a requirement, it warrants a superseding ADR rather than an in-place change.

Redis being down now fails these endpoints closed for token clients. That is the correct direction for a control guarding irreversible operations.

## 4. Deciders

Repository owner, choosing the hybrid option explicitly over API-first-only and session-only alternatives.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **Hybrid: session when present, cache with TTL otherwise** (chosen) | Both client styles work; one expiry rule; no client migration | Two places hold the same state; cache grant outlives token discard |
| Cache/JWT only; drop `SessionAuthentication` to admin-only | Single mechanism; tightest surface | Breaks any existing session-based consumer of the template; discards working behaviour to fix a gap |
| Short-lived dedicated step-up JWT returned by `/me/reauth/` | Stateless; naturally per-device; no server state | Second token type for clients to store and attach; larger client-side change for a template meant to be easy to adopt |
| Session only; remove JWT | Simplest | Contradicts the API-first positioning, the SimpleJWT endpoints and the OpenAPI surface already shipped |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`).*
