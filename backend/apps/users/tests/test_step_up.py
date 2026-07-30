"""Tests for hybrid step-up authentication (ADR-0002).

The defect these pin: `RequiresStepUp` read only `request.session`, while DRF
also accepts stateless `JWTAuthentication`. A bearer-token client never has a
session, so `PATCH /me/secrets/` and `POST /me/anonymize/` were permanently
unreachable for it — the project's own primary authentication mechanism could
not reach its own most-protected endpoints. The pre-existing tests missed this
because they all used `client.force_login`, which establishes a session.
"""

from datetime import timedelta

import pytest
from apps.users import step_up
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import DEFAULT_PASSWORD, VerifiedUserFactory

SECRETS_URL = "/api/v1/users/me/secrets/"
REAUTH_URL = "/api/v1/users/me/reauth/"


@pytest.fixture(autouse=True)
def _clear_cache():
    """Keeps step-up grants from leaking between tests."""
    cache.clear()
    yield
    cache.clear()


def _bearer(user) -> dict[str, str]:
    """Builds the Authorization header for a stateless JWT client.

    Args:
        user: The user to mint an access token for.

    Returns:
        dict[str, str]: Header kwargs for the Django test client.
    """
    access = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


# --------------------------------------------------------------------------
# JWT clients — the path that did not work at all
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_jwt_client_is_denied_without_step_up() -> None:
    """A token client with no re-authentication is refused."""
    user = VerifiedUserFactory()
    client = Client()

    response = client.patch(
        SECRETS_URL,
        {"dni": "11111111H"},
        content_type="application/json",
        **_bearer(user),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_jwt_client_reaches_secrets_after_reauth() -> None:
    """Direct regression: this sequence was impossible before ADR-0002.

    A bearer-token client re-authenticates and then writes a secret. Under the
    session-only implementation the second call always returned 403.
    """
    user = VerifiedUserFactory()
    client = Client()
    headers = _bearer(user)

    reauth = client.post(
        REAUTH_URL,
        {"password": DEFAULT_PASSWORD},
        content_type="application/json",
        **headers,
    )
    assert reauth.status_code == status.HTTP_200_OK

    response = client.patch(
        SECRETS_URL,
        {"dni": "12345678Z"},
        content_type="application/json",
        **headers,
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_jwt_client_denied_after_window_expires() -> None:
    """The grant stops being honoured once the window has passed."""
    user = VerifiedUserFactory()
    client = Client()
    headers = _bearer(user)

    client.post(
        REAUTH_URL,
        {"password": DEFAULT_PASSWORD},
        content_type="application/json",
        **headers,
    )

    # Rewrite the stored grant as though it had been issued long ago. The
    # timestamp is re-validated on read, so shortening the window takes effect
    # for grants already issued.
    stale = (timezone.now() - timedelta(hours=1)).isoformat()
    cache.set(step_up._cache_key(user.pk), stale, timeout=3600)

    response = client.patch(
        SECRETS_URL,
        {"dni": "11111111H"},
        content_type="application/json",
        **headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_wrong_password_grants_nothing() -> None:
    """A failed re-authentication leaves no grant behind."""
    user = VerifiedUserFactory()
    client = Client()
    headers = _bearer(user)

    response = client.post(
        REAUTH_URL,
        {"password": "not-the-password"},
        content_type="application/json",
        **headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert cache.get(step_up._cache_key(user.pk)) is None


# --------------------------------------------------------------------------
# Session clients — must keep working exactly as before
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_session_client_still_works(client) -> None:
    """The pre-existing session flow is unchanged by the hybrid resolution."""
    user = VerifiedUserFactory()
    client.force_login(user)

    assert (
        client.post(
            REAUTH_URL, {"password": DEFAULT_PASSWORD}, content_type="application/json"
        ).status_code
        == status.HTTP_200_OK
    )

    response = client.patch(
        SECRETS_URL,
        {"dni": "11111111H"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_anonymize_is_also_step_up_gated(client) -> None:
    """The irreversible endpoint shares the same gate."""
    user = VerifiedUserFactory()
    client.force_login(user)

    denied = client.post(
        reverse("users:user-anonymize-account"),
        {"confirmation": f"delete {user.email}"},
        content_type="application/json",
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN


# --------------------------------------------------------------------------
# The state module itself
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_revoke_clears_both_backends(rf) -> None:
    """Revocation must not leave one backend still granting."""
    user = VerifiedUserFactory()
    request = rf.post(REAUTH_URL)
    request.session = {}

    # No session_key, so this exercises the cache path only.
    step_up.grant(request, user)
    assert step_up.is_granted(request, user) is True

    step_up.revoke(request, user)

    assert step_up.is_granted(request, user) is False
    assert cache.get(step_up._cache_key(user.pk)) is None


@pytest.mark.django_db
def test_malformed_timestamp_denies(rf) -> None:
    """A corrupt stored value denies rather than raising."""
    user = VerifiedUserFactory()
    request = rf.post(REAUTH_URL)
    request.session = {step_up.SESSION_KEY: "not-a-timestamp"}

    assert step_up.is_granted(request, user) is False
