"""Tests for the registration verification flow (ADR-0004).

The defects these pin: the OTP was written in plaintext into a credential
column — destroying whatever the user had stored there — never expired, and was
emitted to the log stream at INFO. That column has since been removed
(ADR-0005), so the collision case is asserted against `dni`, which shares the
vault.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from users.models import UserSecret, UserSecretAudit
from users.services import VerificationService

from .factories import UserFactory


@pytest.mark.django_db
class TestVerificationStorage:
    """Where and how the code is stored."""

    def test_code_is_encrypted_at_rest(self) -> None:
        """The stored column must not contain the plaintext code."""
        user = UserFactory()

        otp = VerificationService.initialize_verification_flow(user)
        user.secrets.refresh_from_db()

        raw = user.secrets.verification_otp_encrypted
        assert raw, "no ciphertext was written"
        assert otp not in raw, "the code is readable in the stored column"
        assert user.secrets.get_sensitive_data("verification_otp") == otp

    def test_other_vault_fields_survive_verification(self) -> None:
        """Direct regression: issuing a code used to destroy a stored value.

        The OTP borrowed a credential column, so registering a user wiped
        whatever was in it. The code now has its own field and must not touch
        any other.
        """
        user = UserFactory()
        user.secrets.set_sensitive_data("dni", "12345678Z")
        user.secrets.save()

        VerificationService.initialize_verification_flow(user)
        user.secrets.refresh_from_db()

        assert user.secrets.get_sensitive_data("dni") == "12345678Z"

    def test_code_is_cleared_after_success(self) -> None:
        """A consumed code leaves nothing behind."""
        user = UserFactory()
        otp = VerificationService.initialize_verification_flow(user)

        assert VerificationService.verify_account(user, otp) is True

        user.secrets.refresh_from_db()
        assert user.secrets.verification_otp_encrypted is None
        assert user.secrets.verification_otp_expires_at is None


@pytest.mark.django_db
class TestVerificationRules:
    """Acceptance and rejection."""

    def test_correct_code_verifies_the_account(self) -> None:
        user = UserFactory()
        otp = VerificationService.initialize_verification_flow(user)

        assert VerificationService.verify_account(user, otp) is True
        user.refresh_from_db()
        assert user.is_verified is True

    def test_wrong_code_is_rejected(self) -> None:
        user = UserFactory()
        VerificationService.initialize_verification_flow(user)

        assert VerificationService.verify_account(user, "000000") is False
        user.refresh_from_db()
        assert user.is_verified is False

    def test_expired_code_is_rejected(self) -> None:
        """Codes used to be valid forever."""
        user = UserFactory()
        otp = VerificationService.initialize_verification_flow(user)

        user.secrets.verification_otp_expires_at = timezone.now() - timedelta(
            minutes=1
        )
        user.secrets.save(update_fields=["verification_otp_expires_at"])

        assert VerificationService.verify_account(user, otp) is False
        user.refresh_from_db()
        assert user.is_verified is False

    def test_verification_without_a_pending_code_is_rejected(self) -> None:
        user = UserFactory()

        assert VerificationService.verify_account(user, "123456") is False

    def test_success_is_audited(self) -> None:
        """`UserSecretAudit` already existed for exactly this."""
        user = UserFactory()
        otp = VerificationService.initialize_verification_flow(user)

        VerificationService.verify_account(user, otp)

        assert UserSecretAudit.objects.filter(
            user=user, field_affected="verification_otp", action_type="VERIFY"
        ).exists()


@pytest.mark.django_db
class TestCodeGeneration:
    """Properties of the generated code."""

    def test_code_shape(self) -> None:
        code = VerificationService.generate_otp()

        assert len(code) == 6
        assert code.isdigit()

    def test_codes_are_not_repeated(self) -> None:
        """A weak generator would show collisions quickly at this sample size."""
        codes = {VerificationService.generate_otp() for _ in range(200)}

        assert len(codes) > 150, "suspiciously low entropy for a 6-digit space"

    def test_generator_does_not_use_the_random_module(self) -> None:
        """`random` is a Mersenne Twister: predictable from observed output.

        This code gates account verification, so it must come from a CSPRNG.
        """
        from users import services

        assert not hasattr(services, "random"), (
            "services.py imports `random`; OTP and 2FA recovery codes must use `secrets`"
        )


@pytest.mark.django_db
def test_code_is_never_logged(caplog) -> None:
    """The code was previously written to the log stream at INFO."""
    import logging

    user = UserFactory()
    logger = logging.getLogger("users.services")
    emitted: list[str] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            emitted.append(record.getMessage())

    handler = _Collector(level=logging.DEBUG)
    previous_level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        otp = VerificationService.initialize_verification_flow(user)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert not any(otp in message for message in emitted), (
        f"the verification code leaked into the logs: {emitted}"
    )


@pytest.mark.django_db
def test_secret_model_has_no_plaintext_otp_column() -> None:
    """Guards against a future plaintext column creeping back in."""
    columns = {field.name for field in UserSecret._meta.get_fields()}

    assert "verification_otp_encrypted" in columns
    assert "verification_otp" not in columns
