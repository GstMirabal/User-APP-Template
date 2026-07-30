from django.db import models
from django.utils.translation import gettext_lazy as _

from .user import User


class UserSecret(models.Model):
    """Vault for a user's most sensitive data.

    Every value is encrypted at rest with Fernet. Fields that must support
    exact-match lookup carry a companion `*_index` column holding an
    HMAC-SHA256 blind index, so a record can be found without decrypting the
    whole table.

    Values are written and read exclusively through `set_sensitive_data` and
    `get_sensitive_data`; assigning a raw column directly bypasses encryption.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="secrets",
        verbose_name=_("User"),
    )

    # Encrypted identity
    dni_encrypted = models.TextField(
        _("National ID (encrypted)"), blank=True, null=True
    )
    dni_index = models.CharField(
        _("National ID (blind index)"),
        max_length=64,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
    )
    date_of_birth_encrypted = models.TextField(
        _("Date of birth (encrypted)"), blank=True, null=True
    )
    phone_number_encrypted = models.TextField(
        _("Phone number (encrypted)"), blank=True, null=True
    )
    phone_number_index = models.CharField(
        _("Phone number (blind index)"),
        max_length=64,
        db_index=True,
        blank=True,
        null=True,
    )
    phone_verified_at = models.DateTimeField(
        _("Phone verified at"), blank=True, null=True
    )

    # Registration verification code (ADR-0004). Its own encrypted field with
    # an expiry, rather than borrowing a credential column.
    verification_otp_encrypted = models.TextField(
        _("Verification code (encrypted)"), blank=True, null=True
    )
    verification_otp_expires_at = models.DateTimeField(
        _("Verification code expires at"), blank=True, null=True
    )

    # Two-factor authentication
    otp_secret_key = models.CharField(
        _("2FA secret key"), max_length=255, blank=True, null=True
    )
    otp_recovery_codes = models.TextField(
        _("2FA recovery codes"), blank=True, null=True
    )
    updated_at = models.DateTimeField(_("Last updated"), auto_now=True)
    deleted_at = models.DateTimeField(_("Deleted at"), blank=True, null=True, default=None)

    def set_sensitive_data(self, field_name: str, raw_value: str | None) -> None:
        """Encrypts a value into its column, deriving a blind index if one exists.

        Args:
            field_name (str): Logical field name, without the `_encrypted`
                suffix (for example `"dni"`).
            raw_value (str | None): The plaintext value, or None to clear both
                the ciphertext and its index.
        """
        from utils.encryption import encrypt_value, generate_blind_index

        if raw_value is None:
            setattr(self, f"{field_name}_encrypted", None)
            if hasattr(self, f"{field_name}_index"):
                setattr(self, f"{field_name}_index", None)
            return
        encrypted = encrypt_value(raw_value)
        setattr(self, f"{field_name}_encrypted", encrypted)
        if hasattr(self, f"{field_name}_index"):
            setattr(self, f"{field_name}_index", generate_blind_index(raw_value))

    def get_sensitive_data(self, field_name: str) -> str | None:
        """Decrypts a stored value.

        Args:
            field_name (str): Logical field name, without the `_encrypted`
                suffix.

        Returns:
            str | None: The plaintext value, or None when absent or when
                decryption failed.
        """
        import logging

        from cryptography.fernet import InvalidToken
        from utils.encryption import decrypt_value

        logger = logging.getLogger(__name__)
        encrypted_val = getattr(self, f"{field_name}_encrypted", None)

        try:
            return decrypt_value(encrypted_val)
        except InvalidToken:
            logger.critical(
                "Decryption failed for field %s on user %s. Possible MASTER_KEY mismatch.",
                field_name,
                self.user_id,
            )
            return None

    class Meta:
        app_label = "users"
        verbose_name = _("User secret")
        verbose_name_plural = _("User secrets")

    def __str__(self) -> str:
        return f"Secrets for {self.user.username}"


class UserSecretAudit(models.Model):
    """Append-only record of changes to a user's secret vault."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="secret_audits",
        verbose_name=_("User"),
    )
    field_affected = models.CharField(_("Field affected"), max_length=50)
    action_type = models.CharField(_("Action type"), max_length=10)  # UPDATE, DELETE
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_("Source IP"), blank=True, null=True)

    class Meta:
        app_label = "users"
        verbose_name = _("Secret audit entry")
        verbose_name_plural = _("Secret audit entries")
        ordering = ["-timestamp"]
