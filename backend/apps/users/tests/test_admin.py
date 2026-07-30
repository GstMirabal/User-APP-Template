"""Smoke tests over the admin site.

Complements the ``core.E001`` system check: the check proves the forms can be
constructed, these tests prove the pages actually render. A ``FieldError`` in an
inline surfaces here as a 500 on the user change page.
"""

import pytest
from django.contrib import admin
from django.urls import reverse

from .factories import StaffUserFactory, UserFactory


@pytest.fixture
def staff_client(client):
    """Returns a test client logged in as a superuser."""
    client.force_login(StaffUserFactory())
    return client


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model",
    list(admin.site._registry),
    ids=lambda m: f"{m._meta.app_label}.{m._meta.model_name}",
)
def test_admin_changelist_renders(staff_client, model) -> None:
    """Every registered model's changelist responds successfully."""
    url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")

    response = staff_client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_user_change_page_renders(staff_client) -> None:
    """The user change page renders with its inlines.

    Direct regression for the shipped defect: ``UserProfileInline`` declared a
    field belonging to ``User``, and this page returned a 500.
    """
    user = UserFactory()
    url = reverse("admin:users_user_change", args=[user.pk])

    response = staff_client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_user_add_page_renders(staff_client) -> None:
    """The user creation form renders."""
    response = staff_client.get(reverse("admin:users_user_add"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_forbids_user_deletion(staff_client) -> None:
    """Destructive deletion stays blocked; anonymisation is the sanctioned path."""
    user = UserFactory()

    response = staff_client.get(reverse("admin:users_user_delete", args=[user.pk]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_does_not_render_secret_ciphertext(staff_client) -> None:
    """The secret inline must expose indicators, never stored values.

    Regression for a deny-list that named three fields and therefore rendered
    the ciphertext of every other one into the DOM — `dni_encrypted`,
    `date_of_birth_encrypted`, `phone_number_encrypted` and
    `otp_recovery_codes` — while its docstring claimed to be "paranoid".
    """
    user = UserFactory()
    secrets = user.secrets
    secrets.set_sensitive_data("dni", "12345678Z")
    secrets.set_sensitive_data("phone_number", "+34600111222")
    secrets.set_sensitive_data("date_of_birth", "1990-01-01")
    secrets.set_sensitive_data("otp_recovery_codes", "AAAA1111,BBBB2222")
    secrets.otp_secret_key = "JBSWY3DPEHPK3PXP"
    secrets.save()

    body = staff_client.get(
        reverse("admin:users_user_change", args=[user.pk])
    ).content.decode()

    for field in (
        "dni_encrypted",
        "phone_number_encrypted",
        "date_of_birth_encrypted",
        "otp_recovery_codes",
        "otp_secret_key",
        "verification_otp_encrypted",
    ):
        assert f'name="{field}"' not in body, f"{field} is rendered as an input"

    for ciphertext in (
        secrets.dni_encrypted,
        secrets.phone_number_encrypted,
        secrets.date_of_birth_encrypted,
    ):
        assert ciphertext not in body, "stored ciphertext leaked into the page"

    assert secrets.otp_secret_key not in body, "the TOTP secret leaked into the page"

    # Non-vacuity: the inline must actually be on the page, otherwise the
    # assertions above would pass for a page that renders no secret fields.
    assert "has_identity_data" in body, (
        "the secret inline did not render; the assertions above would then pass "
        "vacuously"
    )
