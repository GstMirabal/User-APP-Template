# 🏁 Walkthrough: USERS
**File**: `docs/walkthroughs/USERS_WALKTHROUGH.md` (RA-06 Option B naming)
**Last updated**: Sprint #004

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| pre-#000 | Custom identity model | `User` with UUID PK and email login, plus `Address`, shipped before governance adoption. |
| pre-#000 | Satellite auto-provisioning | `post_save` signal atomically creates `UserProfile` + `UserSecret` on registration. |
| pre-#000 | Encrypted PII vault | Fernet encryption + HMAC-SHA256 blind indexing via `backend/utils/encryption.py`. |
| pre-#000 | TOTP two-factor | Enrolment, recovery codes, anti-replay cache, drift window ±1. |
| pre-#000 | GDPR anonymization | Irreversible PII erasure through `SoftDeleteQuerySet.anonymize()`. |
| pre-#000 | Audit trail | `UserSecretAudit` append-only log; `AuditManager` blocks physical deletion. |
| #000 | Retroactive documentation | Module reverse-engineered into `docs/architecture/USERS_BLUEPRINT.md`. |
| #001 | Admin repaired | `two_factor_enabled` moved to the `User` fieldset it belongs to; user pages render again. |
| #001 | Suite made executable | The nine pre-existing tests ran for the first time and all passed; factories added. |
| #002 | Step-up reachable via JWT | Grant resolves through session or shared cache (ADR-0002); token clients can finally reach gated endpoints. |
| #002 | Verification code secured | Own Fernet-encrypted column with expiry, constant-time compare, audit entry (ADR-0004). |
| #002 | Credentials use a CSPRNG | OTP and 2FA recovery codes moved off `random`. |
| #002 | Admin secret leak closed | `UserSecretInline` converted from deny-list to allow-list of derived indicators. |
| #002 | `/me/reauth/` under Axes | Re-authentication routed through the authentication backend, so lockout applies. |
| #003 | Vault generalised | Exchange columns removed; `/me/secrets/` now writes `dni`, `phone_number`, `date_of_birth` (ADR-0005). |
| #003 | Module in English | Every `verbose_name`, `__str__`, docstring and comment translated. |
| #003 | Celery stub deleted | The framework was never wired; tasks ran synchronously behind a stub. |

## 2. Current state

The identity domain is an installable Django application, not a project. 61 tests pass here against an in-RAM database, and 79 pass with the app vendored into `Django-Pro-Template` — the second number is the one that means anything, because it is the only run that exercises the app somewhere the test harness did not set the table.

Sprint #004's audit found sixteen defects, two of them blocking, in code that three previous sprints had declared clean. The worst was that **no account created through the API could ever be verified**: registration issued a code, encrypted it, dropped the plaintext, and told the user to check an email nothing had sent. A suite of 51 tests passed throughout, because none of them followed a user from registration to a verified account.

Delivery is now announced through `verification_code_issued` and performed by the host. The app does not send mail, and the `users.W001` system check reports a host that has connected nothing — silence being the failure mode, it needed something louder than a paragraph in a contract.

Two further defects were invisible to this repository's own suite and always would have been. The harness declares `DEFAULT_THROTTLE_RATES["sensitive"]`, so every throttled endpoint passed here while returning `500` in a real project; it also configures DRF authentication, hiding that a host must enable `JWTAuthentication` before a bearer client gets past `403`. Both were found by vendoring, not by reading.

Implements: `docs/architecture/USERS_BLUEPRINT.md`. Consumed per `docs/contracts/USERS_CONTRACT.md`.

## 3. Known limitations / tech debt

| Item | Severity | Marked as | Tracked where |
| :--- | :--- | :--- | :--- |
| No resend endpoint for an expired verification code; recovery is administrator re-issue. Needs its own rate limiting. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1-9 |
| A step-up grant is keyed by user id, so it applies to every concurrent session of that user, and survives the client discarding its token until the window lapses (ADR-0002 §3). | Medium | `:tech-debt:` | `ADR-0002` |
| `test_api.py` hardcodes `/api/v1/users/me/2fa/activate/` because `reverse()` does not resolve that nested router action. | Low | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P2-7 |
| No key rotation path: a plain `Fernet(MASTER_KEY)` and a single pepper, so changing either makes stored secrets unreadable and blind indexes unsearchable. | Medium | `:tech-debt:` | `docs/roadmaps/GLOBAL_ROADMAP.md` P1-11 |
| `graphify-out/` still describes the pre-extraction tree; the graph was not rebuilt because `graphify` is not installed locally. | Low | `:tech-debt:` | Sprint #004 log §8 |

**Resolved in Sprint #004**: registration codes undeliverable; throttled endpoints returning 500 in any host; `JWTAuthentication` unstated; axes lockout degraded to per-IP; `language_code` discarded; `anonymize()` leaving profile metadata; TOTP token and user emails in logs. Full list in `docs/audits/AUDIT_004_USERS_APP.md`.

**Resolved in Sprint #003**: exchange-specific columns; Spanish strings; Celery stub; `setup_2fa` shape.

**Resolved in Sprint #002**: step-up unreachable via JWT; OTP plaintext in a credential column; OTP never expiring; OTP in logs; `random` for credentials; `/me/reauth/` outside Axes; admin ciphertext exposure.

## 4. How to operate it

There is nothing to run. The app is installed into a host project — see
*Installing It In Your Project* in the README, and *Host requirements* in
`docs/contracts/USERS_CONTRACT.md`.

To work on the app itself:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

pytest -q            # 61 tests, in-RAM SQLite, no services required
ruff check .         # clean, with the S and G rule sets enabled
```

The suite runs against `tests_harness/`, which deliberately declares neither
`STEP_UP_WINDOW_SECONDS` nor `VERIFICATION_OTP_TTL_MINUTES`, and connects no
receiver for `verification_code_issued`. Each omission is a claim the run
re-proves: that the app defaults those settings itself, and that a host
forgetting delivery is told so.

---
*Updated at every Sprint Closeout touching this module (RA-05).*
