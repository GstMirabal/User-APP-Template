# User-APP-Template: Professional Django Identity Engine

<div align="center">

[![License][license-shield]][license-url]
[![Framework][django-shield]][django-url]
[![API][drf-shield]][drf-url]

</div>

## Overview
User-APP-Template is a high-performance, security-first boilerplate for building modern Django applications with heavy focus on **Identity and Access Management (IAM)**. Extracted and distilled from production environments, this template provides a robust `users` application featuring:

- **JWT Stateless Authentication**: Secure token management with rotation and blacklisting.
- **Enhanced MFA Architecture**: Built-in support for TOTP (Google Authenticator) and verify-at-login flows.
- **Zero-Trust Encryption**: Application-level encryption for sensitive user data (e.g., API keys, secrets).
- **Brute Force Protection**: Native integration with `django-axes` for account lockout policies.
- **Production-Ready Logging**: Structured JSON logging with ISO-8601 timestamps in UTC.

---

## 🏗 Physical Topology

```text
.
├── .agents/                 # Universal-Agents Constitutional Framework
├── backend/
│   ├── apps/
│   │   ├── core/            # Shared logic, validators, and health checks
│   │   └── users/           # Core Security Engine (The User App)
│   ├── config/              # Django settings and routing (Toml-based config)
│   ├── scripts/             # Infrastructure management scripts
│   └── utils/               # App-level encryption and secret generation
├── Makefile                 # Common developer routines
├── docker-compose.yml       # Local infrastructure (PostgreSQL)
├── project_stack.md         # Architecture cache for AI agents
└── requirements.txt         # Dependency manifest
```

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.13+
- Docker & Docker Compose
- [Optional] `uv` for lightning-fast dependency management

### 2. Environment Setup
Copy the configuration template and generate your security keys:

```bash
cp .env.example .env
cp config.toml.example config.toml
# Fill in the keys in config.toml
```

### 3. Usage via Makefile
The `Makefile` serves as the primary entry point for managing the lifecycle of the template:

```bash
# Spin up infrastructure
make db-up

# Apply initial migrations
make migrate

# Launch Development Server
make dev

# Run Quality Control
make lint
make test
```

---

## 🛡 Security Protocol
This repository follows the strict rules dictated by the [Universal-Agents Framework](.agents/global_user_rules.md):
1. **Strict Typing**: All core logic must use Python Type Hinting.
2. **Google Documentation**: Mandatory use of Google Style Docstrings.
3. **Linter Validation**: `ruff` check and format are mandatory before commits.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

<!-- MARKDOWN LINKS -->
[license-shield]: https://img.shields.io/github/license/GstMirabal/User-APP-Template.svg?style=for-the-badge
[license-url]: https://github.com/GstMirabal/User-APP-Template/blob/master/LICENSE.txt
[django-shield]: https://img.shields.io/badge/django-%23092e20.svg?style=for-the-badge&logo=django&logoColor=white
[django-url]: https://www.djangoproject.com/
[drf-shield]: https://img.shields.io/badge/DRF-ff1709?style=for-the-badge&logo=django&logoColor=white
[drf-url]: https://www.django-rest-framework.org/
