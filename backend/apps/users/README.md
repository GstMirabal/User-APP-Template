<div align="center">

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

</div>

<a name="readme-top"></a>

<h3 align="center">CryptoBot Users Application</h3>

<p align="center">
  Security-first Identity and Access Management (IAM) for the CryptoBot Ecosystem.
<br /><br />
<a href="https://github.com/GstMirabal/Cryptobot"><strong>Explore the docs »</strong></a>
<br />
·
<a href="https://github.com/GstMirabal/Cryptobot/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
·
<a href="https://github.com/GstMirabal/Cryptobot/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
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
      <a href="#key-security-features">Key Security Features</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation & Configuration</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#testing">Testing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

## About The Project

The `users` application is the core security engine of CryptoBot. It handles authentication, authorization, and the secure storage of sensitive exchange credentials using a "Zero-Knowledge" inspired architecture where API keys are encrypted at rest and never exposed back through the API.

### Built With

* ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
* ![Django](https://img.shields.io/badge/django-%23092e20.svg?style=for-the-badge&logo=django&logoColor=white)
* ![DRF](https://img.shields.io/badge/DJANGO-REST-ff1709?style=for-the-badge&logo=django&logoColor=white)
* ![JWT](https://img.shields.io/badge/JWT-black?style=for-the-badge&logo=JSON%20web%20tokens)
* ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Key Security Features

* **JWT Authentication**: Stateless session management with rotating refresh tokens.
* **Encryption Vault**: Asymmetric encryption for Binance API keys using a Master Key architecture.
* **OTP Verification**: Mandatory 6-digit code verification for high-risk operations.
* **2FA (TOTP)**: Dual-layer security compatible with Google Authenticator.
* **RBAC (Role-Based Access Control)**: Hierarchical access levels (Free, Premium, Admin).
* **Paranoid Admin**: A custom Django Admin panel that obscures all sensitive keys and prevents accidental deletions.
* **GDPR Compliance**: Irreversible account anonymization and soft-delete managers.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Prerequisites

* Python 3.13+
* Docker & Docker Compose
* PostgreSQL (Running via Docker)

### Installation & Configuration

1. **Clone the repository**
   ```bash
   git clone https://github.com/GstMirabal/Cryptobot.git
   cd Cryptobot
   ```

2. **Environment Setup**
   Configure your `.env` and `config.toml` files with the following keys:
   * `DJANGO_SECRET_KEY`
   * `MASTER_KEY` (32-byte Fernet key)
   * `ENCRYPTION_PEPPER`

3. **Install Dependencies**
   ```bash
   ./venv/bin/pip install -r requirements.txt
   ```

4. **Run Migrations**
   ```bash
   python backend/manage.py migrate
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

### API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/auth/token/` | POST | Obtain JWT tokens. |
| `/api/v1/users/register/` | POST | Initial account creation. |
| `/api/v1/users/verify/` | POST | Verify account with OTP. |
| `/api/v1/users/me/2fa/setup/`| POST | Configure Google Authenticator. |
| `/api/v1/users/me/secrets/` | PATCH | Update encrypted API keys (Write-Only). |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Testing

We use `pytest` and `factory-boy` for testing.

```bash
export DJANGO_SETTINGS_MODULE=config.settings
pytest backend/apps/users/tests.py
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

Gustavo Mirabal Suarez - gst.mirabal@gmail.com

- LinkedIn: [@Gustavo-Mirabal](https://www.linkedin.com/in/gstmirabal/)
- GitHub: [@GstMirabal](https://github.com/GstMirabal)

Project Link: [https://github.com/GstMirabal/Cryptobot](https://github.com/GstMirabal/Cryptobot)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/GstMirabal/Cryptobot.svg?style=for-the-badge
[contributors-url]: https://github.com/GstMirabal/Cryptobot/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/GstMirabal/Cryptobot.svg?style=for-the-badge
[forks-url]: https://github.com/GstMirabal/Cryptobot/network/members
[stars-shield]: https://img.shields.io/github/stars/GstMirabal/Cryptobot.svg?style=for-the-badge
[stars-url]: https://github.com/GstMirabal/Cryptobot/stargazers
[issues-shield]: https://img.shields.io/github/issues/GstMirabal/Cryptobot.svg?style=for-the-badge
[issues-url]: https://github.com/GstMirabal/Cryptobot/issues
[license-shield]: https://img.shields.io/github/license/GstMirabal/Cryptobot.svg?style=for-the-badge
[license-url]: https://github.com/GstMirabal/Cryptobot/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/gstmirabal/
