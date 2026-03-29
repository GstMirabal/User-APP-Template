from __future__ import annotations
import logging
import random
import string
from typing import TYPE_CHECKING, TypedDict

import pyotp
from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from django.db import models
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
        """Generates a random alphanumeric token."""
        return "".join(random.choices(string.digits, k=length))

    @staticmethod
    def initialize_verification_flow(user: User) -> str:
        """
        Creates the activation secret and triggers the mock 'send' log.
        """
        otp = VerificationService.generate_otp()
        user.secrets.api_key_binance_encrypted = "OTP_PENDING:%s" % otp
        user.secrets.save()
        logger.info("--- [MOCK OTP SENT]: %s ---", otp)
        return otp

    @staticmethod
    def verify_account(user: User, code: str) -> bool:
        """Validates the initial verification code."""
        stored_data = user.secrets.api_key_binance_encrypted or ""
        if "OTP_PENDING:%s" % code == stored_data:
            user.is_verified = True
            user.secrets.api_key_binance_encrypted = ""
            user.save(update_fields=["is_verified"])
            user.secrets.save(update_fields=["api_key_binance_encrypted"])
            return True
        return False

    def setup_2fa(user: User) -> Setup2FAResult:
        """
        Initializes a new TOTP secret and generates recovery codes.
        """
        secret = pyotp.random_base32()
        
        # Generate 8 recovery codes (8 chars each)
        recovery_list = [
            "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            for _ in range(8)
        ]
        
        user.secrets.otp_secret_key = secret
        # Store as encrypted CSV
        user.secrets.set_sensitive_data("otp_recovery_codes", ",".join(recovery_list))
        user.secrets.save()

        otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name="CryptoBot"
        )
        
        return {
            "secret": secret,
            "otp_uri": otp_uri,
            "recovery_codes": recovery_list
        }


    @staticmethod
    def verify_2fa(user: User, token: str) -> bool:
        """
        Validates a TOTP token with Drift Protection and Anti-Replay.
        """
        if not user.secrets.otp_secret_key:
            return False
            
        from django.core.cache import cache
        
        # 1. Anti-Replay: Verify if the token was already used in the current window
        cache_key = "totp_used_%s_%s" % (user.id, token)
        if cache.get(cache_key):
            logger.warning("Replay attack detected for user %s with token %s", user.id, token)
            return False
            
        totp = pyotp.TOTP(user.secrets.otp_secret_key)
        is_valid = totp.verify(token, valid_window=1)
        
        if is_valid:
            cache.set(cache_key, True, timeout=60)
            
        return is_valid


