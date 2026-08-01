"""Regression tests for the Sprint #004 audit findings.

Each one was checked to fail against the code as it stood before the fix, not
only to pass after it. A test that only does the second proves nothing: it is
consistent with the defect never having existed.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.checks import run_checks
from django.dispatch import receiver
from django.test import Client, override_settings

from users.events import verification_code_issued

from .factories import VerifiedUserFactory

User = get_user_model()

REGISTER_URL = "/api/v1/users/register/"


@pytest.fixture(autouse=True)
def _clean_state():
    """Clears throttle counters between tests.

    The `sensitive` scope allows 5 requests a minute and its counters live
    in the cache, which outlives a single test.
    """
    cache.clear()
    yield
    cache.clear()


def _register(client: Client, **overrides: object) -> object:
    """Posts a valid registration payload, with any field overridden."""
    payload = {
        "email": "new@example.test",
        "username": "newuser",
        "password": "Str0ng!Passw0rd#2026",
        "password_confirm": "Str0ng!Passw0rd#2026",
    }
    payload.update(overrides)
    return client.post(REGISTER_URL, payload, content_type="application/json")


@pytest.mark.django_db
def test_f001_registration_announces_the_verification_code() -> None:
    """The plaintext code must reach a host receiver.

    It was generated, encrypted and dropped: `register()` discarded the return
    value, no mail was sent and no signal existed, so the stored column — which
    is never read back — held the only copy. Every account created through the
    API was permanently unverifiable.
    """
    seen: list[dict[str, object]] = []

    @receiver(verification_code_issued, weak=False)
    def _capture(sender, user, code, expires_at, **kwargs):
        seen.append({"user": user, "code": code, "expires_at": expires_at})

    try:
        response = _register(Client())
        assert response.status_code == 201, response.content

        assert len(seen) == 1, (
            "the verification code was not announced; a host has no way to "
            "deliver it and the account can never be verified"
        )
        assert seen[0]["code"].isdigit(), seen[0]["code"]
        assert seen[0]["user"].email == "new@example.test"
        assert seen[0]["expires_at"] is not None
    finally:
        verification_code_issued.disconnect(_capture)


@pytest.mark.django_db
def test_f001_the_announced_code_is_the_one_verify_accepts() -> None:
    """Announcing a code that does not work would be worse than none."""
    captured: list[str] = []

    @receiver(verification_code_issued, weak=False)
    def _capture(sender, user, code, expires_at, **kwargs):
        captured.append(code)

    try:
        client = Client()
        _register(client)
        response = client.post(
            "/api/v1/users/verify/",
            {"email": "new@example.test", "code": captured[0]},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        assert User.objects.get(email="new@example.test").is_verified
    finally:
        verification_code_issued.disconnect(_capture)


def test_f001_a_host_with_no_receiver_is_warned() -> None:
    """Silence is the failure mode, so it needs a check rather than a comment."""
    ids = {message.id for message in run_checks()}
    assert "users.W001" in ids, (
        "a project that connects no receiver issues codes that reach nobody, "
        "and nothing told it so"
    )


@override_settings(AXES_USERNAME_FORM_FIELD="email")
def test_f002_axes_misconfiguration_is_warned() -> None:
    """Lockout degrading to per-IP raises nothing, so it needs a check too."""
    ids = {message.id for message in run_checks()}
    assert "users.W002" in ids


@pytest.mark.django_db
def test_f003_the_registration_response_carries_no_placeholder() -> None:
    """`(MOCK LOG)` was returned to real API clients."""
    body = _register(Client()).json()
    assert "MOCK" not in body["detail"].upper(), body["detail"]


@pytest.mark.django_db
def test_f004_language_code_reaches_the_profile() -> None:
    """It was declared, documented, and dropped by `create()`.

    The request returned 201, so a client had no way to notice that its
    preference had been replaced by the default.
    """
    _register(Client(), language_code="es")
    user = User.objects.get(email="new@example.test")
    assert user.profile.language_code == "es", (
        f"asked for 'es', stored {user.profile.language_code!r}"
    )


@pytest.mark.django_db
def test_f005_anonymisation_clears_the_profile_metadata() -> None:
    """`registration_data` survived an operation that promises full erasure."""
    user = VerifiedUserFactory()
    user.profile.registration_data = {
        "email": "real@example.test",
        "ip": "203.0.113.9",
        "full_name": "A Real Person",
    }
    user.profile.last_activity_at = "2026-01-01T00:00:00Z"
    user.profile.save()

    User.objects.filter(id=user.id).anonymize()

    profile = type(user.profile).objects.get(user_id=user.id)
    assert profile.registration_data == {}, profile.registration_data
    assert profile.last_activity_at is None


@pytest.mark.django_db
def test_f005_the_anonymised_address_does_not_name_this_app() -> None:
    """The domain is written into a host's records permanently."""
    user = VerifiedUserFactory()
    User.objects.filter(id=user.id).anonymize()

    anonymised = User.audit_objects.get(id=user.id)
    assert anonymised.email.endswith("@anonymized.invalid"), anonymised.email
    assert "user-app-template" not in anonymised.email


@pytest.mark.django_db
def test_f010_the_default_manager_is_not_used_by_migrations() -> None:
    """A filtered manager in a data migration hides rows without saying so."""
    assert getattr(type(User.objects), "use_in_migrations", False) is False, (
        "User.objects hides soft-deleted rows, so a data migration reaching "
        "for it would silently skip them"
    )
