<div align="center">

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

</div>

<a name="readme-top"></a>

<h3 align="center">User-APP-Template</h3>

<p align="center">
  Security-first Identity and Access Management (IAM) engine for professional Django applications.
<br /><br />
<a href="https://github.com/GstMirabal/User-APP-Template"><strong>Explore the docs »</strong></a>
<br />
·
<a href="https://github.com/GstMirabal/User-APP-Template/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
·
<a href="https://github.com/GstMirabal/User-APP-Template/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
</p>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul><li><a href="#built-with">Built With</a></li></ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation & Configuration</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

## About The Project

User-APP-Template is a high-performance, security-first boilerplate for building modern Django applications with a heavy focus on **Identity and Access Management (IAM)**. Extracted and distilled from production environments, this template provides a robust `users` application.

**Key Features:**
*   **JWT Stateless Authentication**: Token rotation and blacklisting, signed with a key kept separate from `SECRET_KEY`.
*   **TOTP Two-Factor**: Enrolment with recovery codes and cross-worker anti-replay protection.
*   **Step-Up Authentication**: Sensitive writes and irreversible deletion require recent re-authentication, for both session and bearer-token clients.
*   **Encrypted PII at Rest**: Fernet encryption with HMAC blind indexes, so encrypted fields stay searchable by exact match.
*   **GDPR Anonymisation**: Irreversible PII erasure layered on soft deletion, with an append-only audit trail.
*   **Brute Force Protection**: `django-axes` lockout, covering re-authentication as well as login.
*   **Breach-Corpus Passwords**: Argon2 hashing, a 12-character minimum, complexity rules, and rejection of passwords found in public breach data.
*   **Production-Ready Logging**: Structured JSON logging with ISO-8601 timestamps in UTC.

Every module has a Blueprint in [`docs/architecture/`](docs/architecture/), every architectural decision an [ADR](docs/decisions/), and there is a [customization guide](docs/guides/USERS_CUSTOMIZATION_GUIDE.md) explaining which parts are the identity core and which are optional extras you can safely strip.

### Built With

* ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
* ![Django](https://img.shields.io/badge/django-%23092e20.svg?style=for-the-badge&logo=django&logoColor=white)
* ![DRF](https://img.shields.io/badge/django-rest-ff1709?style=for-the-badge&logo=django&logoColor=white)
* ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
* ![PostgreSQL](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
* ![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Prerequisites

*   **Python 3.13+**: Core language.
*   **Docker & Docker Compose**: Infrastructure orchestration.
*   **Git**: Version control.

### Installation & Configuration

1. **Clone the repository**
   ```bash
   git clone https://github.com/GstMirabal/User-APP-Template.git
   cd User-APP-Template
   ```

2. **Install Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt   # runtime set plus test and lint tooling
   ```

3. **Environment Setup**
   ```bash
   cp .env.example .env
   cp config.toml.example config.toml
   python backend/utils/generate_secrets.py   # emits every key you need
   ```

   Paste the generated values into `config.toml`. Four are mandatory:

   | Setting | Section | Why |
   | :--- | :--- | :--- |
   | `DJANGO_SECRET_KEY` | `[django_settings]` | Signs sessions and CSRF tokens. |
   | `MASTER_KEY` | `[security]` | Fernet key encrypting all PII. Losing it makes stored data unrecoverable. |
   | `ENCRYPTION_PEPPER` | `[security]` | Keys the blind indexes that make encrypted fields searchable. |
   | `JWT_SIGNING_KEY` | `[security]` | Signs access tokens. Falls back to `DJANGO_SECRET_KEY` with a startup warning — see [ADR-0003](docs/decisions/ADR-0003-separate-jwt-signing-key.md). |

   Also set `REDIS_URL` in `[cache]` (`redis://127.0.0.1:6381/0` matches the
   bundled `docker-compose.yml`). The cache is a security dependency rather
   than an optimisation: TOTP anti-replay and step-up authentication both need
   state shared across workers, so the project refuses to start with
   `DEBUG=False` and no cache configured — see [ADR-0001](docs/decisions/ADR-0001-shared-cache-backend.md).

4. **Run Infrastructure and Migrations**
   ```bash
   make db-up      # PostgreSQL on 5434, Redis on 6381
   make migrate
   make dev
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

The `Makefile` serves as the primary gateway for common tasks:

```bash
# Launch development server
make dev

# Run full test suite (in-RAM SQLite, no Docker required)
make test

# Code quality check (Ruff)
make lint

# Django system checks, including the admin-integrity check
make check
```

Continuous integration runs the same gates on every push, plus a production
settings smoke test that boots with `DEBUG=False` and asserts the hardening
actually applies.

**API Documentation:** Once running, access the Interactive Swagger UI at `http://localhost:8000/api/docs/swagger/`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

Licensed under the MIT License. See [LICENSE.txt](LICENSE.txt) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

Gustavo Mirabal Suarez - gst.mirabal@gmail.com

- LinkedIn: [@Gustavo-Mirabal](https://www.linkedin.com/in/gstmirabal/)
- GitHub: [@GstMirabal](https://github.com/GstMirabal)
- Twitter: [@GstMirabal](https://x.com/gst_mirabal)

Project Link: [https://github.com/GstMirabal/User-APP-Template](https://github.com/GstMirabal/User-APP-Template)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/GstMirabal/User-APP-Template.svg?style=for-the-badge
[contributors-url]: https://github.com/GstMirabal/User-APP-Template/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/GstMirabal/User-APP-Template.svg?style=for-the-badge
[forks-url]: https://github.com/GstMirabal/User-APP-Template/network/members
[stars-shield]: https://img.shields.io/github/stars/GstMirabal/User-APP-Template.svg?style=for-the-badge
[stars-url]: https://github.com/GstMirabal/User-APP-Template/stargazers
[issues-shield]: https://img.shields.io/github/issues/GstMirabal/User-APP-Template.svg?style=for-the-badge
[issues-url]: https://github.com/GstMirabal/User-APP-Template/issues
[license-shield]: https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge
[license-url]: https://github.com/GstMirabal/User-APP-Template/blob/main/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/gstmirabal/
