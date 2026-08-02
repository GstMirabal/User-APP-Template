# Security policy

This application holds credentials and personal data, so it overrides the
generic [account policy](https://github.com/GstMirabal/.github/blob/main/SECURITY.md)
with what is specific to it.

## Reporting a vulnerability

Report privately through **GitHub Security Advisories**: open the
[Security tab](https://github.com/GstMirabal/Django-Users-App/security/advisories/new)
and choose *Report a vulnerability*. That keeps the report private until a fix
exists.

**Do not open a public issue.** For a defect in an authentication path, the
issue is the exploit.

Include the version or commit, what an attacker gains, and the smallest
sequence that reproduces it. A failing test is the clearest form of all three.

## Supported versions

| Version | Supported |
| :--- | :--- |
| `2.x` | Yes |
| `1.x` | No — a different artefact, a complete Django project rather than this app |

## What this app is responsible for, and what it is not

It is installed into a host project, and the boundary matters when judging
whether something is a vulnerability here.

**This app owns**: encryption and blind indexing of stored secrets, TOTP
enrolment and anti-replay, step-up authentication, verification codes, and the
anonymisation path.

**The host owns**: the database, the cache backend, TLS, the authentication
classes, the session configuration, log destinations, and delivery of
verification codes. `docs/contracts/USERS_CONTRACT.md` lists each requirement
with the consequence of omitting it.

A report is still worth filing when a host requirement is easy to get wrong,
silent when missed, or documented in a way that misleads. Two findings in the
Sprint #004 audit were exactly that shape.

## Known limitations, deliberately not fixed yet

Stating these is the point of this file. None is a secret, and reporting them
again is not necessary.

| Limitation | Consequence |
| :--- | :--- |
| **No key rotation path.** `get_fernet()` builds a plain `Fernet(MASTER_KEY)` and blind indexes use a single `ENCRYPTION_PEPPER`. | Changing either makes every stored secret undecryptable and every index unsearchable. There is no supported migration. Tracked as roadmap item P1-11. |
| **HS256 is symmetric.** | Any service verifying tokens holds the key that mints them. See [ADR-0003](docs/decisions/ADR-0003-separate-jwt-signing-key.md). |
| **Step-up grants are per user, not per device.** | A grant applies to every concurrent session of that user until the window lapses. See [ADR-0002](docs/decisions/ADR-0002-hybrid-step-up-authentication.md) §3. |
| **Anonymisation is irreversible by design.** | `restore()` refuses an anonymised row. This is the intended behaviour, not a defect. |

## If a key is exposed

`MASTER_KEY` and `ENCRYPTION_PEPPER` cannot simply be replaced — see the table
above. Exposure of either means the stored ciphertext must be treated as
readable, and recovery is re-encrypting every row under a new key **while the
old one is still available**. Losing the old key without re-encrypting first
makes the data unrecoverable rather than merely exposed.

Rotating `SIMPLE_JWT["SIGNING_KEY"]` invalidates every outstanding token, which
is the correct response to its disclosure and costs one re-authentication per
client.
