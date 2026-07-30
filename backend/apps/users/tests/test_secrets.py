"""Tests for the generalised secret vault (ADR-0005).

`PATCH /me/secrets/` previously accepted only exchange API credentials, so the
project's most heavily protected write served one named third party. It now
writes the identity fields the vault already held — which no endpoint had ever
exposed.
"""

import pytest
from apps.users.models import UserSecret, UserSecretAudit
from apps.users.services import VerificationService
from django.core.cache import cache
from django.test import Client
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import DEFAULT_PASSWORD, VerifiedUserFactory

SECRETS_URL = "/api/v1/users/me/secrets/"
REAUTH_URL = "/api/v1/users/me/reauth/"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def stepped_up():
    """Returns a client and user that already hold a step-up grant."""
    user = VerifiedUserFactory()
    client = Client()
    access = RefreshToken.for_user(user).access_token
    headers = {"HTTP_AUTHORIZATION": f"Bearer {access}"}
    client.post(
        REAUTH_URL,
        {"password": DEFAULT_PASSWORD},
        content_type="application/json",
        **headers,
    )
    return client, user, headers


@pytest.mark.django_db
class TestVaultWrites:
    def test_identity_fields_are_stored_encrypted(self, stepped_up) -> None:
        client, user, headers = stepped_up

        response = client.patch(
            SECRETS_URL,
            {"dni": "12345678Z", "phone_number": "+34600111222"},
            content_type="application/json",
            **headers,
        )

        assert response.status_code == status.HTTP_200_OK
        user.secrets.refresh_from_db()
        assert user.secrets.get_sensitive_data("dni") == "12345678Z"
        assert user.secrets.get_sensitive_data("phone_number") == "+34600111222"
        assert "12345678Z" not in (user.secrets.dni_encrypted or "")

    def test_blind_index_is_derived(self, stepped_up) -> None:
        """Exact-match lookup must work without decrypting the table."""
        client, user, headers = stepped_up

        client.patch(
            SECRETS_URL,
            {"dni": "12345678Z"},
            content_type="application/json",
            **headers,
        )
        user.secrets.refresh_from_db()

        from utils.encryption import generate_blind_index

        assert user.secrets.dni_index == generate_blind_index("12345678Z")

    def test_each_written_field_is_audited(self, stepped_up) -> None:
        client, user, headers = stepped_up

        client.patch(
            SECRETS_URL,
            {"dni": "12345678Z", "date_of_birth": "1990-01-01"},
            content_type="application/json",
            **headers,
        )

        audited = set(
            UserSecretAudit.objects.filter(user=user).values_list(
                "field_affected", flat=True
            )
        )
        assert {"dni", "date_of_birth"} <= audited

    def test_stored_values_are_never_returned(self, stepped_up) -> None:
        """Write-only means a value can be overwritten but never read back."""
        client, _user, headers = stepped_up

        response = client.patch(
            SECRETS_URL,
            {"dni": "12345678Z"},
            content_type="application/json",
            **headers,
        )

        assert "12345678Z" not in response.content.decode()

    def test_empty_payload_is_rejected(self, stepped_up) -> None:
        client, _user, headers = stepped_up

        response = client.patch(
            SECRETS_URL, {}, content_type="application/json", **headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_exchange_columns_are_gone() -> None:
    """The template must not ship a named third party in its schema."""
    columns = {field.name for field in UserSecret._meta.get_fields()}

    for removed in (
        "api_key_binance_encrypted",
        "api_key_binance_index",
        "api_secret_binance_encrypted",
    ):
        assert removed not in columns, f"{removed} survived the migration"


@pytest.mark.django_db
def test_setup_2fa_is_a_staticmethod() -> None:
    """It was an undecorated instance method annotated as if `self` were a User.

    It worked only because the class attribute resolves to a plain function;
    instantiating the service and calling it would have broken.
    """
    assert isinstance(
        VerificationService.__dict__["setup_2fa"], staticmethod
    ), "setup_2fa is not a staticmethod, unlike every sibling on the service"

    user = VerifiedUserFactory()
    result = VerificationService.setup_2fa(user)

    assert result["secret"]
    assert result["otp_uri"].startswith("otpauth://")
    assert len(result["recovery_codes"]) == 8

    # Calling through an instance must work too, which the old shape prevented.
    assert VerificationService().setup_2fa(VerifiedUserFactory())["secret"]


@pytest.mark.django_db
def test_anonymisation_clears_the_whole_vault() -> None:
    """Every encrypted column must be nulled, not just the ones once listed."""
    from django.contrib.auth import get_user_model

    user = VerifiedUserFactory()
    secrets = user.secrets
    secrets.set_sensitive_data("dni", "12345678Z")
    secrets.set_sensitive_data("phone_number", "+34600111222")
    secrets.set_sensitive_data("date_of_birth", "1990-01-01")
    secrets.otp_secret_key = "JBSWY3DPEHPK3PXP"
    secrets.save()
    VerificationService.initialize_verification_flow(user)

    get_user_model().objects.filter(pk=user.pk).anonymize()

    secrets.refresh_from_db()
    for column in (
        "dni_encrypted",
        "dni_index",
        "phone_number_encrypted",
        "phone_number_index",
        "date_of_birth_encrypted",
        "verification_otp_encrypted",
        "otp_secret_key",
        "otp_recovery_codes",
    ):
        assert getattr(secrets, column) is None, f"{column} survived anonymisation"
