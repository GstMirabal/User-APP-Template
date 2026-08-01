"""Signals this app emits for a host project to act on.

Kept separate from `signals.py`, which holds the receivers this app connects to
Django's own signals. This module is the outbound direction: things the app
announces and deliberately does not handle itself.

Delivery is the clearest example. This app issues verification codes; it does
not know whether a given project reaches its users by email, by SMS, through a
queue or through a provider's API, and choosing for it would mean imposing a
template, a subject line and a set of `EMAIL_*` settings on every consumer.
So the code is announced and the host decides.

The trade-off is real and worth stating plainly: a project that connects no
receiver issues codes that reach nobody. That is what the `users.W001` system
check in `checks.py` exists to catch, at startup rather than in production.
"""

import django.dispatch

#: Sent once a verification code has been issued and stored, with the plaintext
#: code the recipient needs. The app never delivers it.
#:
#: Args:
#:     sender: The user model class.
#:     user: The account the code belongs to.
#:     code (str): The plaintext code. It exists nowhere else — the stored
#:         column is encrypted and never read back — so a receiver that drops
#:         it leaves the account unverifiable.
#:     expires_at (datetime): When the code stops being accepted.
verification_code_issued = django.dispatch.Signal()
