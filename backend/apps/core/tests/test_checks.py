"""Tests for the custom admin-integrity system check.

The defect this check exists for shipped undetected: ``UserProfileInline``
declared ``two_factor_enabled``, a field of ``User`` rather than
``UserProfile``. ``manage.py check`` passed cleanly and the admin change page
returned a 500. These tests pin both halves — that the check stays quiet on a
correct configuration, and that it fires when that exact mistake reappears.
"""

from typing import Any

import pytest
from apps.core.checks import check_admin_forms_are_constructible
from apps.users.admin import UserProfileInline


def test_registered_admins_build_cleanly() -> None:
    """Every registered admin form and inline formset constructs without error."""
    messages = check_admin_forms_are_constructible()
    assert messages == [], f"admin integrity check reported: {messages}"


def test_check_detects_field_belonging_to_another_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reintroducing the original defect must produce a core.E001 error."""
    monkeypatch.setattr(
        UserProfileInline,
        "fields",
        (*UserProfileInline.fields, "two_factor_enabled"),
    )

    messages = check_admin_forms_are_constructible()

    assert any(m.id == "core.E001" for m in messages), (
        "the check failed to flag a field declared on the wrong model"
    )
    assert any("two_factor_enabled" in str(m) for m in messages)


def test_check_reports_unknown_field_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """A field name matching no model at all is also caught."""
    monkeypatch.setattr(
        UserProfileInline,
        "fields",
        (*UserProfileInline.fields, "field_that_does_not_exist"),
    )

    messages: list[Any] = check_admin_forms_are_constructible()

    assert any(m.id == "core.E001" for m in messages)
