# 🔍 Audit 004: `users` application

**Module**: USERS
**Audit Sprint**: #004
**Audit Date**: 2026-08-01
**Audit Commit SHA**: 3668d29
**Scope**: the whole app in its post-extraction form — 1872 lines of source across
19 modules, on Django 6.0.7 with `django-axes` 8.3.1 and `cryptography` 50.0.0.

---

## 1. Why this audit exists

Sprints #001 to #003 fixed a great deal, but each chased a defect it already
knew about. Nothing had ever swept `managers.py`, `signals.py` or `serializers/`
systematically. Those three modules hold six of the fourteen findings below,
including the two most serious.

Every finding was reproduced by execution. None is inferred from reading alone,
and the probe output is quoted where it is the evidence.

## 2. Findings

| # | Finding | Severity |
| :--- | :--- | :--- |
| **F-001** | A registered account can never be verified | **Blocking** |
| **F-002** | Security events reach no handler | **High** |
| **F-003** | `(MOCK LOG)` shipped in a user-facing API response | **High** |
| F-004 | `language_code` is accepted, documented and silently discarded | Medium |
| F-005 | `anonymize()` leaves `registration_data` and `last_activity_at` intact | Medium |
| F-006 | The TOTP token is written to the log on replay detection | Medium |
| F-007 | Three log calls interpolate the user's email with an f-string | Medium |
| F-008 | `restore()` is unreachable through the default manager | Medium |
| F-009 | `except Exception: raise e` handles nothing and logs nothing | Medium |
| F-010 | `use_in_migrations = True` on a manager that hides rows | Medium |
| F-011 | The anonymised-email domain hardcodes the old repository name | Low |
| F-012 | `ruff` selects neither security nor logging rule sets | Low |
| F-013 | `User: AbstractUser = get_user_model()` annotates a class as an instance | Low |
| F-014 | Two docstrings describe behaviour that was deleted, plus two typos | Low |

---

### F-001 · A registered account can never be verified — **Blocking**

`views.py:118` calls `VerificationService.initialize_verification_flow(user)`
and **discards its return value**. That return value is the plaintext
verification code. It is stored encrypted, and the plaintext then goes out of
scope: no email is sent, no signal fires, nothing is returned to the caller,
and the column is write-only by design.

The whole app contains no `send_mail`, no `EmailMessage`, no delivery of any
kind. `grep -rn "send_mail\|EmailMessage" users/` returns nothing.

So the primary onboarding journey terminates. A user registers, receives
`201`, and there is no path — for them or for an administrator through any
shipped interface — to obtain the code that `POST verify/` requires.

```
POST register/  ->  201 {"detail": "User registered successfully.
                          Please check your email (MOCK LOG) to verify..."}
                    code generated, encrypted, plaintext dropped
POST verify/    ->  400 for every possible input
```

The service docstring says the code is returned "for the caller to deliver out
of band", which is a reasonable division of labour for a reusable app — the
host owns delivery. But that seam is not exposed: the view swallows the return
value, so a host has nothing to hook. Neither the contract nor the README tells
a host that delivery is its responsibility.

### F-002 · Security events reach no handler — **High**

Every logger in the app resolves to zero handlers under the settings a host
gets by default:

```
users.views      handlers=0      users.step_up     handlers=0
users.services   handlers=0      users.encryption  handlers=0
users.signals    handlers=0      users.managers    handlers=0
users.models.secrets            handlers=0
```

What is being discarded is not diagnostic noise:

| Event | Level | Where |
| :--- | :--- | :--- |
| Decryption failed — *"Possible MASTER_KEY mismatch"* | `critical` | `models/secrets.py:118` |
| **TOTP replay attack detected** | `warning` | `services.py:177` |
| Failed step-up re-authentication | `warning` | `views.py:89` |
| Irreversible anonymisation started | `warning` | `views.py:284` |
| Invalid verification code presented | `warning` | `services.py:103` |

The first is the app's single most important operational alarm: it means stored
personal data has become unreadable. The second is an active-attack indicator.
Both vanish.

An app cannot configure its host's logging, and should not try. What it can do
— and does not — is state in the contract that a host must register a `users`
logger, and say which records it will lose otherwise.

### F-003 · `(MOCK LOG)` shipped in a user-facing response — **High**

`views.py:126` returns, to real API clients:

> "User registered successfully. Please check your email (MOCK LOG) to verify
> your account."

A development placeholder in production copy. Compounded by F-001, it is also
untrue twice over: there is no email, mock or otherwise.

### F-004 · `language_code` is accepted, documented and discarded — Medium

`UserRegistrationSerializer` declares `language_code`, `USERS_CONTRACT.md`
documents it as *"no — defaults to `en-us`"*, and `create()` never reads it: it
pops `password_confirm` and calls `create_user(email, username, password)`.

```
    language_code pedido:  'es'
    language_code guardado: 'en-us'
```

The request succeeds with `201`, so a client has no way to detect that its
preference was dropped.

### F-005 · `anonymize()` does not clear everything it claims — Medium

The method docstring says it "Clears PII in User, UserProfile, and UserSecret".
`USERS_CONTRACT.md` says "Identity rewritten, every encrypted column nulled".
`UserProfile.registration_data` — a free-form `JSONField` named *Registration
metadata* — is cleared by neither. Nor is `last_activity_at`.

```
    registration_data tras anonymize:
      {'email': 'b@x.test', 'ip': '203.0.113.9', 'full_name': 'Bruno Real', ...}
```

**Calibration matters here.** Nothing in the app ever writes
`_registration_metadata`, so as shipped the column is always `{}` and no data
leaks today. This is a latent defect, not an active breach — and saying
otherwise would be the same overstatement this protocol exists to prevent.

It is still worth fixing, because `signals.py:43` reads that attribute off the
instance precisely as a host extension point. A host that uses the field as its
name invites gets a silent erasure hole in the one feature whose purpose is
erasure, while the docstring assures it otherwise.

### F-006 · The TOTP token is logged — Medium

```python
logger.warning("Replay attack detected for user %s with token %s", user.id, token)
```

A one-time code that has already been spent is of limited value to an attacker,
but this is a credential written to a log, and Sprint #002 closed exactly this
class of defect for the verification code (P0-13). The same reasoning applies;
this instance survived. `user.id` alone identifies the event.

### F-007 · Emails interpolated into logs with f-strings — Medium

`views.py:120`, `views.py:284` and `serializers/registration.py:50` build their
message with an f-string, and all three interpolate `user.email`.

Two problems in one line each. The f-string is evaluated before the logging
call regardless of level, so the cost is paid even when the record is dropped.
And an email address is personal data, in an application built around not
leaking personal data — the rest of the codebase uses `user.pk`, which is what
makes the exception visible.

### F-008 · `restore()` is unreachable through the default manager — Medium

`CustomUserManager.get_queryset()` filters `.alive()`. A soft-deleted row is
therefore invisible to `User.objects`, so `restore()` reached that way can
never match it:

```
    User.objects.restore()   -> 0 | revive: False
    audit_objects.restore()  -> 1 | revive: True
```

The working call is `User.audit_objects.filter(...).restore()`. Nothing
documents that, and `USERS_CONTRACT.md` mentions `restore()` in a way that
implies it works as written.

### F-009 · An except block that handles nothing — Medium

```python
except Exception as e:
    # Atomic rollback is automatic, but we re-raise for awareness.
    raise e
```

`signals.py:62`. Catching and unconditionally re-raising is equivalent to no
handler at all, except that it looks like error handling to a reader. It also
breaches `agents.md §1` (*"No `pass` in except. Explicit logging required"*) —
the rule's intent is that a caught exception is recorded, and this one is
silent. Failure to provision a profile or secret vault is exactly the event
worth logging before it propagates.

### F-010 · `use_in_migrations` on a filtering manager — Medium

`CustomUserManager` sets `use_in_migrations = True` while its `get_queryset()`
restricts to `deleted_at IS NULL` — both confirmed at runtime. A data migration
reaching for `User.objects` therefore silently skips every soft-deleted row.
Django's documentation warns against exactly this pairing.

### F-011 · Old repository name in anonymised addresses — Low

`managers.py:85` builds `f"{anon_id}@user-app-template.internal"`. The domain is
written into the database permanently, and it names a repository that no longer
exists under that name. Same class as the TOTP issuer fixed earlier this
sprint: a reusable app should not stamp its own identity onto a host's data.

### F-012 · The linter has no security or logging rules — Low

`ruff.toml` selects `E, F, W, I, N, UP, B, A, C4, DTZ, SIM, PTH, TD, ERA, PL,
RUF`. It selects neither `S` (flake8-bandit) nor `G` (flake8-logging-format) —
in an identity application. `G` alone would have caught F-007 mechanically.

### F-013 · A type annotation that is false — Low

`signals.py:15` reads `User: AbstractUser = get_user_model()`. The call returns
a model *class*; the correct annotation is `type[AbstractUser]`. The repository
also dropped `mypy --strict` from its declared stack, which is why nothing
caught it.

### F-014 · Documentation of deleted behaviour, and typos — Low

`create_user_profile_and_secrets` says it "schedules post-transaction tasks".
Sprint #003 deleted the Celery stub (P1-5); the docstring outlived it. Also
`atomicallly` (three `l`s) in the same docstring, and `irreversable` in
`views.py:285`.

---

## 3. What was checked and found clean

Recording this matters as much as the findings: it marks where the protocol was
run and produced nothing, so a later reader does not assume it was skipped.

| Technique | Result |
| :--- | :--- |
| Every registered admin form and formset constructed | 7 models, 0 failures |
| Random generators on credential paths | All routed through `secrets`; no `random` |
| Clean environment with only `requirements.txt` | Imports and passes `check`; no undeclared dependency |
| Full-history sweep for committed secrets | Only the harness literals, fixed in `3668d29` |
| Suite executed at every declared dependency floor | 51 pass at each |
| Migration state | `makemigrations --check` reports nothing pending |

## 4. Not covered

- **Concurrency and load.** Cross-worker anti-replay is reasoned about, not
  measured. F-002 aside, nothing here exercises more than one process.
- **Business logic against intent.** This audit verifies that the code does what
  it says. Whether what it says is what is wanted is not a question it can
  answer.
- **The host side.** Every finding is scoped to this app. What a project does
  with it is `Django-Pro-Template`'s audit and its own.

---
*Findings feed `docs/roadmaps/GLOBAL_ROADMAP.md`. Blocking items must close
before Sprint #004 closes (P3 exit criterion 6).*
