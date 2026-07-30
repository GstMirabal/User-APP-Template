# 📋 Sprint Log: #001 — Backend / Verification
**Sprint ID**: 001
**Stack / Layer**: backend / verification
**Date**: 2026-07-30
**Branch**: `ai-sprint/001` (RA-12)
**Commit**: 86cc29b
**Status**: `CLOSED`

---

## 1. Purpose

Restore the project's ability to verify itself. The Sprint #000 audit found a codebase whose design was sound but whose behaviour could not be observed or proved: the test suite never ran, application logs went nowhere, the admin crashed, the health probe always failed, and production mode was unreachable. No business behaviour changes in this sprint.

## 2. Defects repaired

| ID | Defect | Root cause | Verified by |
| :--- | :--- | :--- | :--- |
| B1 | Admin user page returned HTTP 500 | `UserProfileInline.fields` declared `two_factor_enabled`, a field of `User`. Django does not validate inline fields, so `manage.py check` passed clean. | `test_admin.py` (4 tests), `test_checks.py` (3 tests) |
| B2 | `GET /health/` returned 500 unconditionally | `Response(report, status_code=...)`; DRF's signature takes `status=`. The local dict named `status` also shadowed the `rest_framework.status` module. | `test_health.py` (3 tests) |
| B3 | Test suite uncollectable | No `DJANGO_SETTINGS_MODULE` anywhere: no `[tool.pytest.ini_options]`, no `pytest.ini`, no `conftest.py`. `pytest-django` was already installed. | Suite collects and passes |
| B4 | Application logs silently discarded | `LOGGING` declared `django` and `project`; modules call `getLogger(__name__)` yielding `apps.*` / `utils.*`, which resolved to **zero handlers**. | `test_logging.py` (6 tests) |
| B5 | Production mode unreachable | `DEBUG` arrived as a string and was used unconverted. Every non-empty string is truthy, so `DEBUG=False` stayed truthy and the whole `if not DEBUG:` block was dead code. | `test_settings_coercion.py` (15 tests) + CI smoke step |

**B5 was discovered during this sprint**, not in the #000 audit, while preparing the CI configuration. It is the most severe finding of either sprint: the template could not be deployed to production safely as shipped. Any operator setting `DEBUG=False` would have received full tracebacks, no HSTS, no secure cookies, and silently skipped `ALLOWED_HOSTS`, CORS and email guards.

## 3. Prevention added

| Mechanism | Catches |
| :--- | :--- |
| `apps/core/checks.py` (`core.E001` / `core.W001`) | Constructs every registered admin form and inline formset at startup. Turns the B1 class of defect into a boot error instead of a runtime 500. |
| `.github/workflows/ci.yml` — production settings smoke | Boots with `DEBUG=False` and asserts HSTS, SSL redirect and secure cookies actually apply. This is the step that would have caught B5. |
| `.github/workflows/ci.yml` — lint / checks / tests | `ruff check`, `manage.py check --fail-level WARNING`, full suite. |

## 4. Secondary corrections

- `.env` loading switched to `os.environ.setdefault`, so real environment variables win over the file. The previous behaviour let a stray `.env` silently override values injected into a container or CI runner.
- ruff configuration unified in `ruff.toml`. The `[tool.ruff]` block in `pyproject.toml` was dead configuration — ruff resolves `ruff.toml` first — which is why rules its `ignore` list named kept surfacing. Findings: **79 → 0**.
- `AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP` (removed in Axes 6) replaced with `AXES_LOCKOUT_PARAMETERS`.
- Test modules restructured into `tests/` packages; `factory_boy` factories added.
- `make test` runs the whole suite; `make check` added.

## 5. Upstream contribution (`agents.md §4 feedback_upstream`)

`on_commit.py`'s secret scanner matched the bare substrings `API_KEY =`, `SECRET =`, `PASSWORD =` against the uppercased file. That flags every legitimate *read* of a secret — `password = request.data.get("password")`, `EMAIL_HOST_PASSWORD = email_config[...]` — which no project handling authentication can avoid. Seven false positives blocked this sprint's commit with no host-side way to pass.

Fixed on `.agents` branch `fix/secret-scanner-false-positives`: the scanner now requires a secret-named identifier assigned a string **literal**, skipping environment placeholders (`"$VAR"`), obvious placeholders, short values, and test fixtures. Detection also widened to `MASTER_KEY`, `SIGNING_KEY`, `ACCESS_KEY`, `PEPPER` and `CREDENTIAL` — the previous list missed all of them, including `MASTER_KEY`, this project's primary encryption secret.

Validated against 15 cases: 8 legitimate patterns pass, 7 real leak shapes are caught. **Still needs pushing to the `.agents` remote.**

## 6. Metrics

| Metric | Before | After |
| :--- | ---: | ---: |
| Tests collected | 0 | 52 |
| Tests passing | 0 | 52 |
| `ruff` findings | 79 | 0 |
| `manage.py check` warnings | 1 | 0 |
| Application loggers reaching a handler | 0 / 4 | 4 / 4 |
| Working HTTP endpoints among those audited | — | `/health/` restored |
| Graph | 3003 nodes / 3081 edges | 3251 nodes / 3366 edges |

## 7. Governance notes

- Executed entirely on `ai-sprint/001` (RA-12). No direct commit to `main`.
- The baseline history squash requested for `main` remains **unpushed**: `on_commit.py` blocks pushes to `main` outside the deployment workflow, and the human elected to run it manually rather than open the `.deploy_unlock` marker outside its sanctioned use.
- Three P0 items from the #000 roadmap (P0-3 ruff, plus the newly-numbered P0-10/11/12) were pulled forward because CI could not be honest without them.

---
*Closed under RA-05: Blueprints, Global Roadmap, Walkthroughs, and Master Ledger all updated.*
