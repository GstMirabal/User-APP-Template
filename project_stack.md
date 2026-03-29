# Project Stack: User-APP-Template

## Core Technology
- **Language:** Python 3.13+
- **Framework:** Django 5.x
- **API Framework:** Django REST Framework (DRF)
- **Authentication:** JWT (SimpleJWT) + Axes (Brute Force Protection)
- **Documentation:** OAS 3.0 via `drf-spectacular` (Swagger/Redoc)

## Components
- **Identity & Access Management (IAM):** Robust `users` app with support for custom models, MFA (TOTP), and encrypted secrets.
- **Validation:** Enhanced password complexity and security headers (CSP, HSTS).
- **Log Management:** Structured JSON logging in UTC for production readiness.

## Infrastructure & Tooling
- **Database:** PostgreSQL (PostGIS ready if needed).
- **Orchestration:** Docker & Docker Compose.
- **Dependency Manager:** Python standard `pip` + `requirements.txt`.
- **Quality Control:** `ruff` for linting and formatting.

## Operations
- **Dev Server:** `make dev` or `python backend/manage.py runserver`
- **Testing:** `make test` or `pytest backend/apps/users/`
- **Quality Check:** `make lint` or `ruff check backend/`
