# Changelog

All notable changes to User-APP-Template. This file is the **Master Ledger** (agents.md §0): every Sprint Closeout appends its sprint entry under `[Unreleased]`; every deployment seals that section as `[vX.Y.Z] - date` immediately before tagging.

Format: [Keep a Changelog](https://keepachangelog.com/) · Versioning: [SemVer](https://semver.org/).

> Jurisdiction note: framework changes live in `.agents/CHANGELOG.md`, never here. When the `.agents` pin is updated, this ledger records only the bump (e.g. `chore(deps): pin .agents to v4.2.1 #[Sprint_ID]`).

## [Unreleased]

### Added
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
- `.gitignore` extended to exclude the regenerated Claude Code bridge (`/CLAUDE.md`, `/.claude/{agents,commands,skills}/`, `/.claude/settings.local.json`) and `/graphify-out/`. #000
- `chore(deps): pin .agents to v4.2.1` #000

## [0.1.0] - 2026-07-30

_Seed entry: state of the project at governance adoption (Scenario C — audited inherited state)._

**What exists and works**: a Django 5.x / DRF security-first IAM backend. Custom `User` model (UUID PK, email login) with `UserProfile` and `UserSecret` satellites auto-provisioned by an atomic `post_save` signal. PII encrypted at rest with Fernet and made searchable via HMAC-SHA256 blind indexes. TOTP two-factor enrolment with recovery codes and cache-backed anti-replay. GDPR-grade irreversible anonymization layered on soft deletion, with an append-only `UserSecretAudit` trail that refuses physical deletion. Brute-force protection via `django-axes` (5 failures, 15-minute cooloff, user+IP). SimpleJWT HS256 with rotating, blacklisted refresh tokens. Production security headers (HSTS 1 year with preload, CSP, secure/HttpOnly/SameSite cookies). OpenAPI 3.0 through `drf-spectacular`. UTC-normalized structured logging.

**What does not work, as verified in this audit**: the test suite cannot be collected at all (no `pytest-django` configuration), so none of the above has executable verification; `GET /health/` raises `TypeError` on every request due to an invalid `status_code=` kwarg passed to DRF's `Response`; `ruff check backend/` reports 79 findings; step-up authentication is session-backed and therefore unreachable for stateless JWT clients, making `/me/secrets/` and `/me/anonymize/` dead endpoints for them; the registration OTP is stored in plaintext inside the `api_key_binance_encrypted` column. Full detail in the module Walkthroughs; remediation order in `docs/roadmaps/GLOBAL_ROADMAP.md`.
