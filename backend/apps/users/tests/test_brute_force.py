"""Tests that `/me/reauth/` is covered by brute-force protection.

The endpoint called `user.check_password()` directly. `AxesBackend` sits first
in `AUTHENTICATION_BACKENDS` and only counts attempts routed through it, so this
endpoint — a password oracle available to anyone holding a valid token — sat
entirely outside lockout, limited only by the 5/min throttle.
"""

import pytest
from axes.models import AccessAttempt
from django.core.cache import cache
from django.test import Client
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import DEFAULT_PASSWORD, VerifiedUserFactory

REAUTH_URL = "/api/v1/users/me/reauth/"


@pytest.fixture(autouse=True)
def _clean_state():
    """Clears throttle counters and step-up grants between tests."""
    cache.clear()
    yield
    cache.clear()


def _bearer(user) -> dict[str, str]:
    """Builds the Authorization header for a stateless JWT client."""
    access = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


@pytest.mark.django_db
def test_failed_reauth_is_recorded_by_axes() -> None:
    """A failed attempt must reach the Axes backend, not just return 403."""
    user = VerifiedUserFactory()
    client = Client()

    response = client.post(
        REAUTH_URL,
        {"password": "wrong-password"},
        content_type="application/json",
        **_bearer(user),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert AccessAttempt.objects.exists(), (
        "Axes recorded nothing; the endpoint is bypassing the authentication "
        "backend and therefore brute-force protection"
    )


@pytest.mark.django_db
def test_successful_reauth_records_no_failure() -> None:
    """A correct password must not accrue lockout counters."""
    user = VerifiedUserFactory()
    client = Client()

    response = client.post(
        REAUTH_URL,
        {"password": DEFAULT_PASSWORD},
        content_type="application/json",
        **_bearer(user),
    )

    assert response.status_code == status.HTTP_200_OK
    assert not AccessAttempt.objects.filter(username=user.email).exists()


@pytest.mark.django_db
def test_missing_password_is_a_bad_request() -> None:
    """An absent password is a client error, not a failed credential."""
    user = VerifiedUserFactory()
    client = Client()

    response = client.post(
        REAUTH_URL, {}, content_type="application/json", **_bearer(user)
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not AccessAttempt.objects.exists()
