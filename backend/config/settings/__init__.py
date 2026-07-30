"""Settings package.

Split out of a single 700-line module so each concern is separately readable.
The modules form a chain, each re-exporting the previous one, because the
values genuinely depend on each other in this order:

    base -> security -> cache -> email_config -> third_party -> logging_config

`base` loads `config.toml` and defines the project skeleton. `security`
resolves DEBUG, which `cache` and `email` both branch on. `third_party` needs
the signing keys `security` produced. `logging` comes last because it reads
DEBUG for its levels.

Importing the last link therefore pulls in everything.

`email_config` and `logging_config` carry the suffix deliberately: modules named
`email.py` or `logging.py` inside a package shadow the standard library ones for
any relative import, which is a failure that surfaces far from its cause.
"""

from .logging_config import *

# Underscore-prefixed names are not carried by `import *`, and this one is
# imported directly by the coercion tests.
from .security import _as_bool  # noqa: F401
