# Changelog

All notable changes to django-users-app. This file is the **Master Ledger** (agents.md §0): every Sprint Closeout appends its sprint entry under `[Unreleased]`; every deployment seals that section as `[vX.Y.Z] - date` immediately before tagging.

Format: [Keep a Changelog](https://keepachangelog.com/) · Versioning: [SemVer](https://semver.org/).

> Jurisdiction note: framework changes live in `.agents/CHANGELOG.md`, never here. When the `.agents` pin is updated, this ledger records only the bump (e.g. `chore(deps): pin .agents to v4.2.1 #[Sprint_ID]`).

## [Unreleased]

_Nothing yet._

## [1.0.0] - 2026-07-30

First release of the template as a verifiable, deployable and generic Django
user-management foundation. Consolidates Sprints #000-#003.

**Breaking**: migration `0007` irreversibly drops `api_key_binance_encrypted`,
`api_key_binance_index` and `api_secret_binance_encrypted`. Export any data in
those columns before migrating ([ADR-0005](docs/decisions/ADR-0005-generic-secret-vault.md)).

**Fixed during release**: `Pillow` was never declared in `requirements.txt`
despite `UserProfile.avatar` being an `ImageField`. A fresh clone failed
`manage.py check` with `fields.E210`; it worked locally only because the
dependency had been installed by hand. Caught by CI on its first real run.

**Required configuration**: `REDIS_URL` in `[cache]` — the project refuses to
start with `DEBUG=False` and no shared cache ([ADR-0001](docs/decisions/ADR-0001-shared-cache-backend.md)).
`JWT_SIGNING_KEY` in `[security]` is strongly recommended; without it the
project falls back to `DJANGO_SECRET_KEY` and warns at startup
([ADR-0003](docs/decisions/ADR-0003-separate-jwt-signing-key.md)).

### Added
- **Customization guide** (`docs/guides/USERS_CUSTOMIZATION_GUIDE.md`) stating which components are the identity core and which are optional extras, with exactly what breaks when each is removed. #003
- `requirements-dev.txt`, so a deployment no longer installs pytest, factory-boy and ruff alongside its runtime dependencies. #003
- [ADR-0005](docs/decisions/ADR-0005-generic-secret-vault.md): generic secret vault, without exchange-specific columns. #003
- Four architecture decision records under `docs/decisions/`, the project's first recorded rationale. #002
- `apps/users/step_up.py`, holding step-up grant state shared between the permission class and the re-authentication endpoint. #002
- `STEP_UP_WINDOW_SECONDS` and `VERIFICATION_OTP_TTL_MINUTES` settings, replacing hardcoded values. #002
- **Executable test suite.** `[tool.pytest.ini_options]` plus `config/settings_test.py` running against an in-RAM SQLite database (`agents.md §3 local_testing`). The suite went from *uncollectable* to 52 passing tests; the nine pre-existing tests were correct all along and had simply never run. #001
- **Custom system check** (`apps/core/checks.py`, `core.E001`) that constructs every registered admin form and inline formset at startup, turning the admin-crash class of defect into a boot-time error instead of a runtime 500. #001
- **Continuous integration** (`.github/workflows/ci.yml`): lint, Django system checks at `--fail-level WARNING`, the test suite, and a production-settings smoke test that boots with `DEBUG=False` — the step that would have caught the unreachable-production defect. #001
- `factory_boy` factories for the users app (`UserFactory`, `VerifiedUserFactory`, `StaffUserFactory`). #001
- Adopted Token-Optimized Agent Pipeline governance (`.agents` v4.2.1) — onboarding scenario: **C (mature project, no prior agents)**. Full reverse engineering of the inherited Django IAM backend. #000
- `docs/` tree instantiated: `architecture/`, `roadmaps/`, `walkthroughs/`, `sprints/`, `decisions/`, `guides/`, `contracts/`. #000
- `docs/0_SYSTEM_OVERVIEW.md` — Documentation Entry Point with C4 Level 1-2 diagrams. #000
- `docs/active_state.json` — Zero Coordinate anchor, including `code_containers` declaration for the `backend` stack and computed C4 Level 3 eligibility (advisory: `users` qualifies, density 2.89 vs `core` 1.78). #000
- Blueprints (arc42-lite, Reference): `USERS_BLUEPRINT.md`, `CORE_BLUEPRINT.md`, `CONFIG_BLUEPRINT.md`. #000
- Walkthroughs recording verified current state and tech debt: `USERS_WALKTHROUGH.md`, `CORE_WALKTHROUGH.md`, `CONFIG_WALKTHROUGH.md`. #000
- `docs/roadmaps/GLOBAL_ROADMAP.md` — P0/P1/P2 remediation backlog derived from the audit. #000
- `docs/sprints/000-backend-identity/` — onboarding audit record and graph statistics snapshot. #000
- `.agents/venv_skillopt/` provisioned with the lean core (`graphifyy==0.8.30`); `.agents/installed.lock` written. #000

### Changed
- **Removed the exchange-specific columns.** `api_key_binance_encrypted`, `api_key_binance_index` and `api_secret_binance_encrypted` were the only fields `UserSecretSerializer` exposed, so the project's most heavily protected write existed solely to store credentials for one named exchange. The serializer now writes the identity fields the vault already held — `dni`, `phone_number`, `date_of_birth` — which no endpoint had ever exposed. Migration `0007` is irreversible ([ADR-0005](docs/decisions/ADR-0005-generic-secret-vault.md)). #003
- **Split `settings.py` into a package.** 704 lines mixing configuration loading, secrets, security headers, database, cache, email, third-party wiring and logging became six modules chained in dependency order. All 198 resolved settings were dumped before and after: 196 byte-identical, two private helpers correctly not exported, one class module path changed. #003
- **Translated every Spanish string in code to English** (`agents.md §1 code_logic`). Migration `0008` carries the `verbose_name` changes; no schema effect. #003
- **Deleted the Celery stub.** `config/celery_app.py` never existed, so `tasks.py` fell back to a `CeleryStub` and every task ran synchronously; `signals.py` carried a matching closure with an empty body. #003
- `VerificationService.setup_2fa` is a `@staticmethod`, matching every sibling on the service. It was an undecorated instance method annotated as if `self` were a `User`. #003
- README documented the pre-#002 setup: no Redis, no `[cache]` section, no `JWT_SIGNING_KEY`, and a feature list still describing exchange API key storage. #003
- **Unified ruff configuration in `ruff.toml`.** The `[tool.ruff]` block in `pyproject.toml` was dead configuration — `ruff` resolves `ruff.toml` first — which is why rules its `ignore` list named kept surfacing. Findings dropped from 79 to zero. #001
- Test modules restructured into `tests/` packages per app. #001
- `make test` runs the whole suite instead of a single file; added `make check`. #001
- `chore(deps): pin .agents` to a secret-scanner fix. The commit hook matched the bare substring `PASSWORD =`, flagging every legitimate read of a secret (`password = request.data.get("password")`), which no project handling authentication can avoid. It now requires a secret-named identifier assigned a string *literal*, and additionally detects `MASTER_KEY`, `SIGNING_KEY` and `ENCRYPTION_PEPPER`, which the previous patterns missed entirely. #001
- `.gitignore` extended to exclude the regenerated Claude Code bridge (`/CLAUDE.md`, `/.claude/{agents,commands,skills}/`, `/.claude/settings.local.json`) and `/graphify-out/`. #000
- `chore(deps): pin .agents to v4.2.1` #000

### Fixed
- **Django admin no longer crashes.** `UserProfileInline` declared `two_factor_enabled`, a field of `User` rather than `UserProfile`, so every user change page returned HTTP 500. Django's own checks do not validate inline fields, so `manage.py check` reported nothing. #001
- **`GET /health/` no longer returns 500 unconditionally.** The view passed `status_code=` to DRF's `Response`, which accepts `status=`; every request raised `TypeError`, including the healthy path. #001
- **Application logs are no longer discarded.** `LOGGING` declared only the `django` and `project` loggers while modules call `getLogger(__name__)` (`apps.*`, `utils.*`), so those records reached zero handlers — silently dropping the decryption-failure `CRITICAL`, the TOTP replay warning and the anonymization audit trail. #001
- **Production mode is reachable.** `DEBUG` arrived from `config.toml` as a string and was used unconverted; every non-empty string is truthy, so `DEBUG=False` stayed truthy and the entire `if not DEBUG:` hardening block — HSTS, secure cookies, SSL redirect, plus the `ALLOWED_HOSTS`, CORS and email production guards — was unreachable code. Boolean coercion now rejects ambiguous values loudly. #001
- `.env` loading uses `setdefault`, so variables already present in the real environment win over the file. The previous behaviour let a stray `.env` silently override values injected into a container or CI runner. #001
- Replaced the removed `AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP` with `AXES_LOCKOUT_PARAMETERS`. #001

### Security
- **Step-up authentication reachable for token clients.** `RequiresStepUp` read only `request.session`, while DRF also accepts stateless `JWTAuthentication`. A bearer-token client never has a session, so `PATCH /me/secrets/` and `POST /me/anonymize/` were permanently unreachable for it. Resolution now checks the session and then a shared-cache grant with a TTL ([ADR-0002](docs/decisions/ADR-0002-hybrid-step-up-authentication.md)). #002
- **TOTP anti-replay holds across workers.** No `CACHES` setting existed, so Django fell back to a per-process `LocMemCache`; a replayed token routed to a different worker found an empty cache and was accepted. Adds a Redis service and an explicit cache configuration ([ADR-0001](docs/decisions/ADR-0001-shared-cache-backend.md)). #002
- **`/me/reauth/` is under brute-force protection.** It called `user.check_password()` directly, and `AxesBackend` only counts attempts routed through the authentication backend — leaving a password oracle outside lockout, bounded only by the 5/min throttle. #002
- **JWT signing key separated from `SECRET_KEY`.** Sharing them made disclosure of the session-signing secret an immediate token-forgery capability, and forced both to rotate together ([ADR-0003](docs/decisions/ADR-0003-separate-jwt-signing-key.md)). #002
- **Verification code no longer stored in plaintext in a credential column.** The OTP was written as `OTP_PENDING:<code>` into `api_key_binance_encrypted`, destroying any exchange key the user had stored, never expiring, and bypassing encryption in a column named `_encrypted`. It now has its own Fernet-encrypted field with a TTL, constant-time comparison and an audit entry ([ADR-0004](docs/decisions/ADR-0004-dedicated-encrypted-otp-storage.md)). #002
- **Verification codes and 2FA recovery codes use a CSPRNG.** Both drew from `random`, a Mersenne Twister whose output is predictable from a handful of observed values. #002
- **Admin no longer renders secret ciphertext.** `UserSecretInline` used a deny-list naming three fields and therefore exposed `dni_encrypted`, `date_of_birth_encrypted`, `phone_number_encrypted` and `otp_recovery_codes` in the DOM, contradicting its own docstring. Replaced by an allow-list of derived indicators. #002
- **Verification codes are no longer logged.** Inert while logs reached no handler; repairing logging in #001 turned a latent leak live. #002
- Wired `pwned-passwords-django`, an installed but unused dependency, into `AUTH_PASSWORD_VALIDATORS`. #002
## [0.1.0] - 2026-07-30

_Seed entry: state of the project at governance adoption (Scenario C — audited inherited state)._

**What exists and works**: a Django 5.x / DRF security-first IAM backend. Custom `User` model (UUID PK, email login) with `UserProfile` and `UserSecret` satellites auto-provisioned by an atomic `post_save` signal. PII encrypted at rest with Fernet and made searchable via HMAC-SHA256 blind indexes. TOTP two-factor enrolment with recovery codes and cache-backed anti-replay. GDPR-grade irreversible anonymization layered on soft deletion, with an append-only `UserSecretAudit` trail that refuses physical deletion. Brute-force protection via `django-axes` (5 failures, 15-minute cooloff, user+IP). SimpleJWT HS256 with rotating, blacklisted refresh tokens. Production security headers (HSTS 1 year with preload, CSP, secure/HttpOnly/SameSite cookies). OpenAPI 3.0 through `drf-spectacular`. UTC-normalized structured logging.

**What does not work, as verified in this audit**: the test suite cannot be collected at all (no `pytest-django` configuration), so none of the above has executable verification; `GET /health/` raises `TypeError` on every request due to an invalid `status_code=` kwarg passed to DRF's `Response`; `ruff check backend/` reports 79 findings; step-up authentication is session-backed and therefore unreachable for stateless JWT clients, making `/me/secrets/` and `/me/anonymize/` dead endpoints for them; the registration OTP is stored in plaintext inside the `api_key_binance_encrypted` column. Full detail in the module Walkthroughs; remediation order in `docs/roadmaps/GLOBAL_ROADMAP.md`.
