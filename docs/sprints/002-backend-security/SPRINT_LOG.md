# 📋 Sprint Log: #002 — Backend / Security
**Sprint ID**: 002
**Stack / Layer**: backend / security
**Date**: 2026-07-30
**Branch**: `ai-sprint/002` (RA-12)
**Commit**: aa4e5db
**Status**: `CLOSED`

---

## 1. Purpose

Close the seven P0 security defects carried out of the Sprint #000 audit. Sprint #001 made the project verifiable; this sprint makes it defensible. No new product behaviour.

## 2. Decisions recorded

| ADR | Decision | Triggers |
| :--- | :--- | :--- |
| [ADR-0001](../../decisions/ADR-0001-shared-cache-backend.md) | Redis as the shared cache backend | 3, 6 |
| [ADR-0002](../../decisions/ADR-0002-hybrid-step-up-authentication.md) | Hybrid step-up authentication | 2, 3 |
| [ADR-0003](../../decisions/ADR-0003-separate-jwt-signing-key.md) | Separate JWT signing key from `SECRET_KEY` | 3 |
| [ADR-0004](../../decisions/ADR-0004-dedicated-encrypted-otp-storage.md) | Dedicated encrypted storage for the verification OTP | 1, 3 |

All four escalate to full MADR: trigger #3 fires individually under `rules/documentation_standard.md §3.2`.

## 3. Defects closed

| ID | Defect | Consequence before the fix | Verified by |
| :--- | :--- | :--- | :--- |
| P0-4 | `RequiresStepUp` read only `request.session` | `PATCH /me/secrets/` and `POST /me/anonymize/` unreachable for every bearer-token client — the project's own primary auth could not reach its own most-protected endpoints | `test_step_up.py` (8 tests) |
| P0-5 | OTP stored as plaintext in `api_key_binance_encrypted` | Registering a user destroyed any exchange credential they had stored; plaintext sat in a column named `_encrypted`; codes never expired | `test_verification.py` (13 tests) |
| P0-6 | `SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY` | Disclosure of the session secret was simultaneously arbitrary token forgery; the two could not rotate independently | CI production smoke |
| P0-7 | No `CACHES`, so per-process `LocMemCache` | TOTP anti-replay did not hold across workers; the health probe reported on a dict that cannot fail | CI production smoke + local Redis round-trip |
| P0-8 | `/me/reauth/` called `check_password()` directly | A password oracle outside Axes lockout, bounded only by the 5/min throttle | `test_brute_force.py` (3 tests) |
| P0-9 | `UserSecretInline` used a deny-list of three fields | Ciphertext of `dni`, `date_of_birth`, `phone_number` and `otp_recovery_codes` rendered into the admin DOM, contradicting its own "paranoid" docstring | `test_admin.py::test_admin_does_not_render_secret_ciphertext` |
| P0-13 | OTP written to logs at `INFO` | Inert only because Sprint #001 found logs reached no handler; repairing logging turned a latent leak live | `test_verification.py::test_code_is_never_logged` |

## 4. Defects found during the sprint

Neither appeared in the #000 audit.

**Weak randomness for authentication credentials.** `VerificationService.generate_otp` and the 2FA recovery-code generator both drew from `random.choices`. `random` is a Mersenne Twister: its internal state is recoverable from a modest number of observed outputs, after which all future values are predictable. These are account-verification codes and two-factor recovery credentials. Both now use `secrets`, and a test asserts the module never imports `random` again.

**Session leakage in the first step-up draft.** `grant()` initially wrote the session unconditionally. Because `SessionMiddleware` persists any modified session, a bearer-token request would have received a `Set-Cookie` and created a session record per re-authentication — silently turning a stateless client stateful and growing the session store without bound. Caught by `test_jwt_client_denied_after_window_expires`, which failed because the test client retained the cookie. `grant()` now writes the session only when one already exists.

## 5. Verification

Every regression test was checked in both directions where the fix was structural. `test_admin_does_not_render_secret_ciphertext` was run against the restored deny-list and **fails**, then against the allow-list and passes; it also asserts the inline renders at all, so the absence assertions cannot pass vacuously.

The CI production smoke step now boots with `DEBUG=False` against a real Redis service and asserts the signing key is distinct from `SECRET_KEY`, the cache backend is not per-process, and the breach-corpus validator is active.

## 6. Metrics

| Metric | Sprint #001 | Sprint #002 |
| :--- | ---: | ---: |
| Tests | 52 | 77 |
| `ruff` findings | 0 | 0 |
| `manage.py check` warnings | 0 | 0 |
| ADRs | 0 | 4 |
| Migrations | 5 | 6 |
| Graph | 3251 / 3366 | 3433 / 3613 |

## 7. Operator actions required

| Action | Why |
| :--- | :--- |
| Add a `[cache]` section to `config.toml` with `REDIS_URL` | Without it, `DEBUG=False` now refuses to boot — deliberately, since a per-process cache voids TOTP anti-replay |
| Set `JWT_SIGNING_KEY` in `[security]` | Otherwise it falls back to `SECRET_KEY` with a startup warning. Setting it for the first time invalidates outstanding tokens once |
| Run `make migrate` | Migration `0006` adds the OTP columns |
| Re-verify users mid-registration | Codes held in the old location are not migrated (ADR-0004 §3) |

## 8. Deferred

- No resend endpoint exists for an expired verification code; the recovery path is administrator re-issue. Needs its own rate limiting, so it is not bundled here.
- The Binance columns remain. Removing them is a destructive migration scheduled for Sprint #003, kept separate so a security fix is not entangled with a cleanup.
- HS256 remains symmetric: any service verifying tokens must hold the key that mints them. A move to RS256 warrants its own ADR.

---
*Closed under RA-05: Blueprints, Global Roadmap, Walkthroughs, and Master Ledger all updated.*
