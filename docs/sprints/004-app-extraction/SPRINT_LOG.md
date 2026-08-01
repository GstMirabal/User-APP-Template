# 📋 Sprint Log: #004 — App / Extraction

**Sprint ID**: 004
**Stack**: app
**Layer**: extraction
**Opened**: 2026-07-31
**Closed**: 2026-08-01
**Branch**: `ai-sprint/004`

---

## 1. Purpose

Stop this repository being a Django project.

It was one, and duplicating one: fifteen scaffolding files shared with
`Django-Pro-Template`, all fifteen diverged. Every scaffold fix had to be made
twice and in practice was made once. What is original here is the `users` app,
so that is what the repository now contains.

## 2. Decisions recorded

| Decision | Where |
| :--- | :--- |
| Verification codes are announced, not delivered | `users/events.py`, contract *Host requirements* |
| The app supplies its own `sensitive` throttle rate | `users/throttling.py` |
| `django-axes` floored at 8.3, skipping 7.x | `requirements.txt` |
| Dependency floors state what was executed, not what is expected to work | `requirements.txt` |
| ADR-0003 superseded rather than deleted | `docs/decisions/ADR-0003-*.md` |
| Renamed to `django-users-app` | Repository metadata |

## 3. Work completed

| # | Item |
| :--- | :--- |
| P3.2 | `backend/apps/users/` flattened to `users/`; scaffolding deleted; `tests_harness/` created |
| P3.2 | `utils/encryption.py` moved to `users/encryption.py` — identity logic, not shared plumbing |
| P3.2 | `users/defaults.py`: app-level fallbacks so a host declares only what it changes |
| P3.2 | `docs/contracts/USERS_CONTRACT.md` written — referenced since Sprint #000, never authored |
| P3.2 | Dependencies raised and every floor executed; `dependabot.yml` added |
| P3.2 | CI reduced to a call of `Django-Pro-Template`'s reusable workflow in `app` mode |
| P3.2 | Banner wired, README rewritten as installation instructions, dead issue links fixed |
| P3.3 | Deep audit: sixteen findings, `AUDIT_004_USERS_APP.md` |
| P3.4 | All sixteen closed; twelve regression tests, each checked to fail without its fix |
| P3.4 | Integration: 79 tests green with the app vendored into `Django-Pro-Template` |

## 4. What the audit found that reading would not have

Six of the sixteen findings sit in `managers.py`, `signals.py` and
`serializers/` — the three modules no previous sprint had swept, because each
had been chasing a defect it already knew about.

The worst, F-001, is that **no account created through the API could ever be
verified**. `register()` discarded the plaintext code, nothing sent it, and the
stored column is never read back. The response said to check your email. A
suite of 51 tests passed throughout, because none of them followed a user from
registration to a verified account.

## 5. What the harness was hiding

F-015 and F-016 were invisible here and would have stayed invisible. The
harness declares `DEFAULT_THROTTLE_RATES["sensitive"]`, so every throttled
endpoint passed while returning `500` in a real project. It also configures DRF
authentication, hiding that a host must enable `JWTAuthentication` before a
bearer client gets past `403`.

A harness is a stand-in host. One that is too helpful conceals the requirements
it exists to expose — which is the argument for vendoring into the real
scaffold being a gate rather than a formality.

## 6. Metrics

| Measure | Before | After |
| :--- | ---: | ---: |
| Source lines (app only) | 1872 | 2164 |
| Tests | 85 (project) | 61 (app) + 79 (integrated) |
| Scaffolding files duplicated with `Django-Pro-Template` | 15 | 0 |
| Blocking findings open | 2 (unknown) | 0 |
| Host requirements documented | 4 | 7 |
| `ruff` rule sets | 16 | 18 (`S`, `G`) |

## 7. Operator actions required

A project upgrading from `v1.0.0` is not upgrading — it is installing something
else. There is no migration path from the project to the app, and none is
offered.

A project installing the app must supply what
`docs/contracts/USERS_CONTRACT.md` lists under *Host requirements*. Two of
those are reported by `manage.py check` as `users.W001` and `users.W002`;
the rest fail visibly or not at all.

## 8. Deferred

| Item | Why |
| :--- | :--- |
| P1-11 · key rotation | `MultiFernet` is the mechanism; it is a feature, not a fix, and warrants its own ADR |
| P1-9 · code resend endpoint | Needs its own rate limiting; out of scope for an extraction sprint |
| U-2, U-3 | Framework findings, drafted against `.agents` rather than fixed here |
| Graph rebuild | `graphify-out/` still describes the pre-extraction tree; `graphify` is not installed locally |
