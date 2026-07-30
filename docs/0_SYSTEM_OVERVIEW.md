# 🧭 System Overview: User-APP-Template
**Last Audit Sprint**: #000
**Last Audit Date**: 2026-07-30
**Last Audit Commit SHA**: b27b5c2

This is the **Documentation Entry Point**. `agents.md §0 (Entry Point)` requires every session to read this file before anything else. It is intentionally short — for the full component inventory, see `.agents/docs/architecture/topology_map.md`.

---

## 1. What this is

**User-APP-Template** is a security-first Identity and Access Management (IAM) engine for Django applications: a reusable backend template providing custom user identity, encrypted PII storage, TOTP two-factor authentication, GDPR anonymization, and brute-force protection.

This project uses the **Token-Optimized Agent Pipeline (`.agents`)** framework as a git submodule: a governance layer that determines how AI subagents plan, execute, and hand off work here. Governance was adopted in Sprint #000 via the Scenario C (mature project, no prior agents) onboarding route.

| Aspect | Value |
| :--- | :--- |
| **Language / Runtime** | Python 3.13 |
| **Framework** | Django 5.x + Django REST Framework |
| **Datastore** | PostgreSQL 15 (Docker, host port `5434`) |
| **Auth** | SimpleJWT (HS256) + `django-axes` + TOTP (`pyotp`) |
| **API docs** | OAS 3.0 via `drf-spectacular` |
| **Quality** | `ruff` (lint/format), `mypy --strict` |

## 2. Architecture at a glance (C4 Level 1-2)

**Level 1 — Context**: this system and who/what it talks to outside its own boundary.

```
                    +---------------------+
   API client  ---> |                     | ---> PostgreSQL 15  (identity + encrypted PII)
   (web / mobile)   |  User-APP-Template  | ---> Django cache    (TOTP anti-replay, health)
                    |    IAM backend      | ---> Celery broker   (declared, not wired)
   Django admin --> |                     |
                    +---------------------+
                              |
                              v
                   Authenticator app (TOTP enrolment via otpauth:// URI)
```

**Level 2 — Container**: the deployable pieces this system is built from.

| Container | Path | Responsibility |
| :--- | :--- | :--- |
| **`users`** | `backend/apps/users/` | Identity domain: User/Profile/Secret models, registration, 2FA, anonymization. |
| **`core`** | `backend/apps/core/` | Cross-cutting primitives: health check, password complexity validator. |
| **`config`** | `backend/config/` | Django project configuration: settings, root URLConf, WSGI/ASGI. |
| **`utils`** | `backend/utils/` | Cryptographic helpers: Fernet encryption, HMAC blind indexing. |
| **`db`** | `docker-compose.yml` | PostgreSQL 15 container, volume `./.docker-db-data`. |

Component-level (Level 3) detail, where required, lives per-module in the relevant `[MODULE]_BLUEPRINT.md` — see `rules/documentation_standard.md §2.1`. For this project, C4 Level 3 runs in **advisory mode** (bootstrap, §2.1 rule 8); the `users` container is the single qualifying container of the `backend` stack (density 2.89 vs `core` 1.78, safety floor applied with 2 containers).

## 3. The governance hierarchy

| Layer | Location | Role |
| :--- | :--- | :--- |
| **Governance Rules** | `.agents/agents.md` | The absolute, transversal rules. Nothing overrides this. |
| **Rules** | `.agents/rules/*.md` | Domain-specific standards (QA, topology, skills, security, documentation). |
| **Workflows** | `.agents/workflows/*.md` | Step-by-step protocols, invoked as `/agents:<name>` slash commands. |
| **Subagents** | `.agents/agents/*.md` | The roles that execute workflow steps (Principal, Orchestrator, QA, Tester, etc.). |
| **Skills** | `.agents/skills/*/` | Concrete tools subagents call into (linters, scaffolders, auditors). |

## 4. How a session starts

Run `/agents:start`. It will:
1. Read `agents.md` and this file (Zero-Memory anchor).
2. Install/verify the Claude Code bridge (`.agents/scripts/install_claude.sh`) if not already done.
3. Reconcile `docs/active_state.json` (the anchor wins over `.agent_state/mirror.json`).
4. Hand off to the Principal Agent for Planning (drafting the Implementation Plan with you).

## 5. Where state lives

- `docs/active_state.json` — this project's own session anchor (Zero Coordinate).
- `CHANGELOG.md` (root) — the **Master Ledger**: sprint entries at close, version seals at deployment.
- `docs/roadmaps/`, `docs/sprints/` — this project's own historical record.
- `.agents/docs/` — the framework's own (separate) self-documentation; its changelog is `.agents/CHANGELOG.md`, a different jurisdiction.

## 6. Documentation index

| Document | Type | Covers |
| :--- | :--- | :--- |
| `docs/architecture/USERS_BLUEPRINT.md` | Reference | Identity domain (models, endpoints, crypto, anonymization). |
| `docs/architecture/CORE_BLUEPRINT.md` | Reference | Health check and password complexity validator. |
| `docs/architecture/CONFIG_BLUEPRINT.md` | Reference | Settings, security headers, JWT/Axes/throttling, routing. |
| `docs/walkthroughs/*_WALKTHROUGH.md` | Historical | What works today, verified how, and known tech debt. |
| `docs/roadmaps/GLOBAL_ROADMAP.md` | Future | Prioritized remediation and feature backlog. |
| `docs/sprints/000-backend-identity/` | History | The Scenario C onboarding audit record. |

## 7. Full inventory

For the detailed component-by-component map of what lives inside `.agents/`, read `.agents/docs/architecture/topology_map.md`.
