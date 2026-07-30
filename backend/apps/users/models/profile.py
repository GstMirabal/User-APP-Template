from django.db import models
from django.utils.translation import gettext_lazy as _

from .user import User


class UserProfile(models.Model):
    """User profile containing preferences, configuration, and consent."""

    class UserRole(models.TextChoices):
        FREE = "free", _("Free")
        PREMIUM = "premium", _("Premium")
        ADMIN = "admin", _("Admin")

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("Usuario"),
    )
    role = models.CharField(
        _("Rol de usuario"),
        max_length=15,
        choices=UserRole.choices,
        default=UserRole.FREE,
    )

    # Preferencias
    timezone = models.CharField(_("Zona Horaria"), max_length=100, default="UTC")
    preferred_currency = models.CharField(
        _("Moneda Preferida"), max_length=10, default="USD"
    )
    language_code = models.CharField(_("Idioma"), max_length=10, default="en-us")
    avatar = models.ImageField(_("Avatar"), upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(_("Biografía"), blank=True, null=True)
    email_notifications_enabled = models.BooleanField(
        _("Notificaciones por email"), default=True
    )

    # Consentimiento Legal
    accepted_terms_at = models.DateTimeField(
        _("Términos aceptados el"), blank=True, null=True
    )
    accepted_privacy_policy_at = models.DateTimeField(
        _("Privacidad aceptada el"), blank=True, null=True
    )
    marketing_consent = models.BooleanField(
        _("Consentimiento de marketing"), default=False
    )
    registration_data = models.JSONField(
        _("Datos de registro"), default=dict, blank=True
    )
    last_activity_at = models.DateTimeField(
        _("Última actividad"), blank=True, null=True
    )
    deleted_at = models.DateTimeField(
        _("Fecha de borrado"), blank=True, null=True, default=None
    )

    class Meta:
        app_label = "users"
        verbose_name = _("Perfil de Usuario")
        verbose_name_plural = _("Perfiles de Usuario")

    def __str__(self) -> str:
        return f"Perfil de {self.user.username}"
