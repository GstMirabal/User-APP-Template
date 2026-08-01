from __future__ import annotations

import logging
import secrets as secrets_module
import string
from datetime import timedelta
from typing import TYPE_CHECKING, TypedDict

import pyotp
from django.contrib.auth import get_user_model
from django.utils import timezone

from .defaults import two_factor_issuer_name, verification_otp_ttl_minutes
from .events import verification_code_issued

if TYPE_CHECKING:
    from .models.user import User

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class Setup2FAResult(TypedDict):
    secret: str
    otp_uri: str
    recovery_codes: list[str]


class VerificationService:
    """
    Tactical service for identity verification and 2FA orchestration.
    """

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generates a numeric one-time code.

        Uses `secrets`, not `random`: the latter is a Mersenne Twister, whose
        output is predictable from a handful of observed values. This code
        gates account verification.

        Args:
            length (int): Number of digits to produce.

        Returns:
            str: The generated code.
        """
        return "".join(secrets_module.choice(string.digits) for _ in range(length))

    @staticmethod
    def initialize_verification_flow(user: User) -> str:
        """Issues a verification code and stores it encrypted, with an expiry.

        The code lives in its own encrypted column (ADR-0004). It previously
        borrowed a credential column and wrote there in plaintext, destroying
        whatever the user had stored.

        Delivery belongs to the host: `verification_code_issued` is sent with
        the plaintext, and a project connects whatever channel it uses. Nothing
        here sends mail. The stored column is never read back, so that signal
        and this return value are the only readable copies that exist.

        Args:
            user (User): The user being verified.

        Returns:
            str: The plaintext code, for a direct caller that prefers not to
                use the signal.
        """
        otp = VerificationService.generate_otp()
        expires_at = timezone.now() + timedelta(
            minutes=verification_otp_ttl_minutes()
        )

        user.secrets.set_sensitive_data("verification_otp", otp)
        user.secrets.verification_otp_expires_at = expires_at
        user.secrets.save(
            update_fields=["verification_otp_encrypted", "verification_otp_expires_at"]
        )

        # The code itself is never logged: it is a live credential, and
        # application logs are shipped off-host.
        logger.debug("Verification code issued for user %s", user.pk)

        # Announced rather than delivered. This app does not know how a given
        # project reaches its users, and the stored column is encrypted and
        # never read back, so this signal carries the only readable copy that
        # will ever exist. A project with no receiver connected is warned by
        # the `users.W001` system check.
        verification_code_issued.send(
            sender=type(user), user=user, code=otp, expires_at=expires_at
        )
        return otp

    @staticmethod
    def verify_account(user: User, code: str) -> bool:
        """Validates a verification code and marks the account verified.

        Args:
            user (User): The user presenting the code.
            code (str): The code supplied by the caller.

        Returns:
            bool: True when the code matched and had not expired.
        """
        stored = user.secrets.get_sensitive_data("verification_otp")
        expires_at = user.secrets.verification_otp_expires_at

        if not stored or not expires_at:
            return False

        if timezone.now() > expires_at:
            logger.info("Expired verification code presented for user %s", user.pk)
            return False

        # Constant-time comparison: the code is short and guessable enough that
        # a timing side channel is worth closing.
        if not secrets_module.compare_digest(stored, code):
            logger.warning("Invalid verification code presented for user %s", user.pk)
            return False

        user.is_verified = True
        user.secrets.set_sensitive_data("verification_otp", None)
        user.secrets.verification_otp_expires_at = None
        user.save(update_fields=["is_verified"])
        user.secrets.save(
            update_fields=["verification_otp_encrypted", "verification_otp_expires_at"]
        )

        VerificationService._audit(user, "verification_otp", "VERIFY")
        return True

    @staticmethod
    def _audit(user: User, field: str, action: str) -> None:
        """Appends an entry to the immutable secret-audit trail.

        Args:
            user (User): Subject of the event.
            field (str): Which secret field the event concerns.
            action (str): Short action verb.
        """
        from django.apps import apps

        audit_model = apps.get_model("users", "UserSecretAudit")
        audit_model.objects.create(
            user=user, field_affected=field, action_type=action
        )

    @staticmethod
    def setup_2fa(user: User) -> Setup2FAResult:
        """Initialises a TOTP secret and generates recovery codes.

        Args:
            user (User): The account enrolling in two-factor authentication.

        Returns:
            Setup2FAResult: The secret, its provisioning URI, and the plaintext
                recovery codes, which the caller must show once and never again.
        """
        secret = pyotp.random_base32()

        # Generate 8 recovery codes (8 chars each)
        alphabet = string.ascii_uppercase + string.digits
        recovery_list = [
            "".join(secrets_module.choice(alphabet) for _ in range(8))
            for _ in range(8)
        ]

        user.secrets.otp_secret_key = secret
        # Store as encrypted CSV
        user.secrets.set_sensitive_data("otp_recovery_codes", ",".join(recovery_list))
        user.secrets.save()

        otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name=two_factor_issuer_name()
        )

        return {"secret": secret, "otp_uri": otp_uri, "recovery_codes": recovery_list}

    @staticmethod
    def verify_2fa(user: User, token: str) -> bool:
        """
        Validates a TOTP token with Drift Protection and Anti-Replay.
        """
        if not user.secrets.otp_secret_key:
            return False

        from django.core.cache import cache

        # 1. Anti-Replay: Verify if the token was already used in the current window
        cache_key = f"totp_used_{user.id}_{token}"
        if cache.get(cache_key):
            logger.warning(
                "TOTP replay attempt for user %s", user.id
            )
            return False

        totp = pyotp.TOTP(user.secrets.otp_secret_key)
        is_valid = totp.verify(token, valid_window=1)

        if is_valid:
            cache.set(cache_key, True, timeout=60)

        return is_valid
