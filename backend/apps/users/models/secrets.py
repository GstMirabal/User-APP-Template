from django.db import models
from django.utils.translation import gettext_lazy as _
from .user import User

class UserSecret(models.Model):
    """Secret vault for highly sensitive user data."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="secrets", verbose_name=_("Usuario")
    )

    # Identidad Cifrada
    dni_encrypted = models.TextField(_("DNI / NIF (Cifrado)"), blank=True, null=True)
    dni_index = models.CharField(_("DNI / NIF (Índice)"), max_length=64, unique=True, db_index=True, blank=True, null=True)
    date_of_birth_encrypted = models.TextField(_("Fecha de nacimiento (Cifrado)"), blank=True, null=True)
    phone_number_encrypted = models.TextField(_("Teléfono (Cifrado)"), blank=True, null=True)
    phone_number_index = models.CharField(_("Teléfono (Índice)"), max_length=64, db_index=True, blank=True, null=True)
    phone_verified_at = models.DateTimeField(_("Teléfono verificado el"), blank=True, null=True)

    # Credenciales Exchanges
    api_key_binance_encrypted = models.TextField(_("Binance API Key (Cifrada)"), blank=True, null=True)
    api_key_binance_index = models.CharField(_("Binance API Key (Índice)"), max_length=64, db_index=True, blank=True, null=True)
    api_secret_binance_encrypted = models.TextField(_("Binance API Secret (Cifrada)"), blank=True, null=True)

    # Seguridad 2FA
    otp_secret_key = models.CharField(_("Clave secreta 2FA"), max_length=255, blank=True, null=True)
    otp_recovery_codes = models.TextField(_("Códigos de recuperación 2FA"), blank=True, null=True)
    updated_at = models.DateTimeField(_("Última actualización"), auto_now=True)
    deleted_at = models.DateTimeField(_("Fecha de borrado"), blank=True, null=True, default=None)

    def set_sensitive_data(self, field_name: str, raw_value: str | None) -> None:
        from utils.encryption import encrypt_value, generate_blind_index
        if raw_value is None:
            setattr(self, f"{field_name}_encrypted", None)
            if hasattr(self, f"{field_name}_index"): setattr(self, f"{field_name}_index", None)
            return
        encrypted = encrypt_value(raw_value)
        setattr(self, f"{field_name}_encrypted", encrypted)
        if hasattr(self, f"{field_name}_index"):
            setattr(self, f"{field_name}_index", generate_blind_index(raw_value))

    def get_sensitive_data(self, field_name: str) -> str | None:
        from utils.encryption import decrypt_value
        from cryptography.fernet import InvalidToken
        import logging
        
        logger = logging.getLogger(__name__)
        encrypted_val = getattr(self, f"{field_name}_encrypted", None)
        
        try:
            return decrypt_value(encrypted_val)
        except InvalidToken:
            logger.critical("Decryption failed for field %s on user %s. Possible MASTER_KEY mismatch.", field_name, self.user_id)
            return None

    class Meta:
        app_label = "users"
        verbose_name = _("Secretos de Usuario")
        verbose_name_plural = _("Secretos de Usuarios")

    def __str__(self) -> str:
        return f"Secretos de {self.user.username}"


class UserSecretAudit(models.Model):
    """Immutable audit log for changes to user secrets."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="secret_audits", verbose_name=_("Usuario")
    )
    field_affected = models.CharField(_("Campo afectado"), max_length=50)
    action_type = models.CharField(_("Tipo de acción"), max_length=10) # UPDATE, DELETE
    timestamp = models.DateTimeField(_("Fecha y hora"), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_("IP del cambio"), blank=True, null=True)

    class Meta:
        app_label = "users"
        verbose_name = _("Auditoría de Secrecto")
        verbose_name_plural = _("Auditorías de Secrectos")
        ordering = ["-timestamp"]

