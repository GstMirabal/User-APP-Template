"""Tests for boolean coercion of configuration values.

`config.toml` templates its values as strings (`DEBUG = "$DEBUG"`), and every
non-empty string is truthy in Python. Before coercion existed, setting
`DEBUG=False` produced the string `"False"` — still truthy — so Django stayed in
debug mode and the entire `if not DEBUG:` hardening block (HSTS, secure cookies,
SSL redirect, and the ALLOWED_HOSTS/CORS/email production guards) was
unreachable code.
"""

import pytest
from config.settings import _as_bool
from django.core.exceptions import ImproperlyConfigured


@pytest.mark.parametrize(
    "raw",
    ["False", "false", "FALSE", "0", "no", "off", "", None, False],
)
def test_falsy_spellings_coerce_to_false(raw: object) -> None:
    """Every accepted falsy spelling must yield False, not a truthy string."""
    assert _as_bool(raw, "DEBUG") is False


@pytest.mark.parametrize("raw", ["True", "true", "TRUE", "1", "yes", "on", True])
def test_truthy_spellings_coerce_to_true(raw: object) -> None:
    """Every accepted truthy spelling must yield True."""
    assert _as_bool(raw, "DEBUG") is True


def test_the_original_defect_is_fixed() -> None:
    """Direct regression: the string "False" must not be truthy after coercion."""
    assert bool("False") is True, "plain Python truthiness, shown for contrast"
    assert _as_bool("False", "DEBUG") is False


@pytest.mark.parametrize("raw", ["maybe", "2", "disabled", "enabled"])
def test_unrecognised_values_are_rejected_loudly(raw: str) -> None:
    """An ambiguous value must abort startup rather than silently pick a side."""
    with pytest.raises(ImproperlyConfigured, match="must be a boolean"):
        _as_bool(raw, "DEBUG")
