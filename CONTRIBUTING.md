# Contributing

The [account guide](https://github.com/GstMirabal/.github/blob/main/CONTRIBUTING.md)
covers the general workflow. This file covers what is specific to a reusable
app, and one trap that has already cost this repository two blocking defects.

## Getting set up

There is no project to run. This repository is the `users` package plus the
tests that prove it.

```bash
git clone --recurse-submodules https://github.com/GstMirabal/django-users-app.git
cd django-users-app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

pytest -q       # 61 tests, in-RAM SQLite, no database or cache service
ruff check .
```

`--recurse-submodules` matters: `.agents` carries the governance tooling, and
the documentation gate breaks without it.

## The trap: the harness lies by being helpful

`tests_harness/` stands in for a host project. It is the smallest configuration
under which the app runs — and every convenience added to it hides a
requirement a real host would have to meet.

That is not hypothetical. In Sprint #004 the harness declared
`DEFAULT_THROTTLE_RATES["sensitive"]`, so registration, verification and
re-authentication all passed here while returning **`500`** in a real project.
It also configured DRF authentication, hiding that a host must enable
`JWTAuthentication` before a bearer client gets past `403`.

So:

- **Do not add settings to the harness to make a test pass.** If the app needs
  a setting, either default it in `users/defaults.py` or add it to *Host
  requirements* in `docs/contracts/USERS_CONTRACT.md` — with a system check in
  `users/checks.py` when its absence is silent.
- The omissions in the harness are deliberate and commented. `STEP_UP_WINDOW_SECONDS`
  and `VERIFICATION_OTP_TTL_MINUTES` are unset so each run proves the app
  defaults them; no receiver is connected for `verification_code_issued` so
  `users.W001` demonstrably fires.
- **A change that touches the app/host boundary must be checked by vendoring**
  the `users/` package into a real project and running its suite. That is the
  only step that exercises the app where the harness did not set the table.

## What a good change looks like

- **A regression test checked to fail without the fix.** Not only to pass with
  it: a test that does the second alone is consistent with the defect never
  having existed. Revert your fix, watch the test fail, restore it.
- **A test that asserts the code, not the environment.** One test written in
  Sprint #004 read `run_checks()` and asserted a warning was present. It passed
  in the harness and failed the moment the app was vendored into a host that
  had correctly wired delivery — it was testing the surroundings.
- **No new host requirement without a check or a contract row.** Preferably
  both. A requirement that fails silently is a defect with a delay on it.
- **No new dependency without the reason in the pull request body.** Floors in
  `requirements.txt` state what the suite was executed against *and* what is
  clear of published advisories. Passing tests do not clear a CVE.

## Documentation

`docs/contracts/USERS_CONTRACT.md` is what consumers read. If behaviour or
configuration changes, it changes in the same pull request — not the one after.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/) with a
`#[Sprint_ID]` suffix:

```
fix(users): announce the verification code instead of dropping it #004
```

Explain **why** in the body. The diff already says what.
