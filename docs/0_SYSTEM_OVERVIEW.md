# 🧭 System Overview: django-users-app
**Last Audit Sprint**: #004
**Last Audit Date**: 2026-08-01
**Last Audit Commit SHA**: 0a71a8c

This is the **Documentation Entry Point**. `agents.md §0 (Entry Point)` requires every session to read this file before anything else. It is intentionally short — for the full component inventory, see `.agents/docs/architecture/topology_map.md`.

---

## 1. What this is

**django-users-app** is a reusable Django application for identity and access management: custom user identity, encrypted personal data, TOTP two-factor authentication, GDPR anonymisation and brute-force protection.

**It is an app, not a project.** Since Sprint #004 this repository holds the `users` package and the tests that prove it, and nothing else — no `manage.py`, no settings module, no compose file. Everything a running system needs comes from the host project that installs it. [`Django-Pro-Template`](https://github.com/GstMirabal/Django-Pro-Template) is the scaffold it is developed and integration-tested against.

This repository uses the **Token-Optimized Agent Pipeline (`.agents`)** framework as a git submodule: a governance layer that determines how AI subagents plan, execute, and hand off work here. Governance was adopted in Sprint #000 via the Scenario C (mature project, no prior agents) onboarding route.

| Aspect | Value |
| :--- | :--- |
| **Language / Runtime** | Python 3.13 |
| **Framework** | Django 5.2 LTS to 6.0, verified at both ends of the range |
| **API layer** | Django REST Framework |
| **Datastore** | The host's choice. The suite runs on in-RAM SQLite. |
| **Cache** | The host must supply one shared across workers — a security dependency, not an optimisation (ADR-0001) |
| **Auth** | SimpleJWT (HS256) + `django-axes` + TOTP (`pyotp`) |
| **Quality** | `ruff` (lint), `pytest` against `tests_harness/` |
| **CI** | Calls the reusable workflow published by `Django-Pro-Template` in `app` mode |

## 2. Architecture at a glance (C4 Level 1-2)

**Level 1 — Context**: the app, its host, and what it reaches outside that boundary.

```
              +------------------------------------------+
              |            HOST PROJECT                  |
              |   settings · urls · database · cache      |
              |                                          |
 API client ->|   +----------------------------------+   |
 (web/mobile) |   |          users (this app)        |   |--> HIBP range API
              |   |  identity · 2FA · vault · GDPR   |   |    (breach-corpus check)
 Django admin |   +----------------------------------+   |
              +------------------------------------------+
                        |                    |
                        v                    v
              host's database        Authenticator app
              (identity + ciphertext)  (otpauth:// URI)
```

Everything outside the inner box is a **host requirement**, specified in [`docs/contracts/USERS_CONTRACT.md`](contracts/USERS_CONTRACT.md). The app does not choose a database, a cache backend or a web server.

**Level 2 — Container**: one container, which is the point.

| Container | Path | Responsibility |
| :--- | :--- | :--- |
| **`users`** | `users/` | The whole app: User/Profile/Secret models, registration, 2FA, encryption, anonymisation. |
| *(harness)* | `tests_harness/` | Not shipped. A minimal stand-in host so the suite can run without a real project. |

The `core`, `config`, `utils`, `db` and `redis` containers listed here before Sprint #004 left with the scaffolding. `core` and `config` are documented in `Django-Pro-Template` from its own code; `utils/encryption.py` moved inside this app as `users/encryption.py`, being identity logic rather than shared plumbing.

C4 Level 3 runs in **advisory mode**: with a single container there is nothing to rank by density. Component detail lives in [`USERS_BLUEPRINT.md`](architecture/USERS_BLUEPRINT.md).

## 3. The governance hierarchy

| Layer | Location | Role |
| :--- | :--- | :--- |
| **Governance Rules** | `.agents/agents.md` | The absolute, transversal rules. Nothing overrides this. |
| **Rules** | `.agents/rules/*.md` | Domain-specific standards (QA, topology, skills, security, documentation). |
| **Workflows** | `.agents/workflows/*.md` | Step-by-step protocols, invoked as `/agents:<name>` slash commands. |
| **Subagents** | `.agents/agents/*.md` | The roles that execute workflow steps (Principal, Orchestrator, QA, Tester, etc.). |
| **Skills** | `.agents/skills/*/` | Concrete tools subagents call into (linters, scaffolders, auditors). |
| **Decisions** | `docs/decisions/ADR-*.md` | This project's own architecture decision records. |

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
| `docs/contracts/USERS_CONTRACT.md` | Reference | The REST surface and what a host must provide. |
| `docs/walkthroughs/USERS_WALKTHROUGH.md` | Historical | What works today, verified how, and known tech debt. |
| `docs/roadmaps/GLOBAL_ROADMAP.md` | Future | Prioritized remediation and feature backlog. |
| `docs/sprints/000-backend-identity/` | History | The Scenario C onboarding audit record. |
| `docs/sprints/001-backend-verification/` | History | Repair of five blocking defects; test harness and CI restored. |
| `docs/sprints/002-backend-security/` | History | Seven P0 security defects closed; first four ADRs. |
| `docs/decisions/ADR-*.md` | Explanation | Recorded rationale, immutable once accepted. |

## 7. Full inventory

For the detailed component-by-component map of what lives inside `.agents/`, read `.agents/docs/architecture/topology_map.md`.
