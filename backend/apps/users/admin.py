from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, UserSecret


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = _("Perfil del Usuario")
    fk_name = "user"
    fields = ("role", "timezone", "preferred_currency", "language_code", "two_factor_enabled")


class UserSecretInline(admin.StackedInline):
    """
    Inline paranoico para secretos.
    NO muestra las llaves reales en el admin para evitar fugas visuales.
    Solo permite ver si el secreto existe y está configurado.
    """
    model = UserSecret
    can_delete = False
    verbose_name_plural = _("Bóveda de Secretos (Solo Lectura)")
    fk_name = "user"
    
    # Excluimos API keys reales para que ni el admin pueda verlas en el DOM
    exclude = ("api_key_binance_encrypted", "api_secret_binance_encrypted", "otp_secret_key")
    
    readonly_fields = ("has_binance_keys",)

    def has_binance_keys(self, obj):
        return bool(obj.api_key_binance_encrypted and obj.api_secret_binance_encrypted)
    has_binance_keys.boolean = True
    has_binance_keys.short_description = _("Binance Keys Configuradas")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Administración central de usuarios blindada.
    """
    inlines = (UserProfileInline, UserSecretInline)
    
    list_display = ("email", "username", "is_verified", "is_suspended", "get_role", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active", "is_verified", "profile__role")
    
    search_fields = ("email", "username")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (_("Información Personal"), {"fields": ("first_name", "last_name", "last_ip_address")}),
        (_("Permisos y Estado"), {
            "fields": ("is_active", "is_verified", "is_suspended", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
        (_("Auditoría"), {"fields": ("date_joined", "last_login", "failed_login_attempts", "password_changed_at")}),
    )

    readonly_fields = ("date_joined", "last_login", "last_ip_address", "failed_login_attempts", "password_changed_at")

    def get_role(self, obj):
        return obj.profile.role if hasattr(obj, "profile") else "-"
    get_role.short_description = _("Rol")

    def has_delete_permission(self, request, obj=None):
        """Bloqueo de borrado destructivo desde el admin (Usar Anonymize/SoftDelete)."""
        return False
