from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, UserSecret


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = _("User profile")
    fk_name = "user"
    fields = (
        "role",
        "timezone",
        "preferred_currency",
        "language_code",
    )


class UserSecretInline(admin.StackedInline):
    """Read-only presence indicators for the secret vault.

    Allow-list, not deny-list. The previous `exclude` named three fields and
    therefore rendered the ciphertext of every other one — `dni_encrypted`,
    `date_of_birth_encrypted`, `phone_number_encrypted`, `otp_recovery_codes`
    — straight into the admin DOM, contradicting the docstring that claimed
    otherwise. A deny-list also leaks again the moment a column is added,
    which is exactly what happened.

    Nothing here exposes a stored value: every field is a derived boolean or a
    timestamp.
    """

    model = UserSecret
    can_delete = False
    verbose_name_plural = _("Secret vault (read-only)")
    fk_name = "user"

    fields = (
        "has_identity_data",
        "has_two_factor",
        "phone_verified_at",
        "updated_at",
    )
    readonly_fields = fields

    @admin.display(boolean=True, description=_("Identity data stored"))
    def has_identity_data(self, obj: UserSecret) -> bool:
        """Reports whether any encrypted identity field is populated."""
        return bool(
            obj.dni_encrypted
            or obj.date_of_birth_encrypted
            or obj.phone_number_encrypted
        )

    @admin.display(boolean=True, description=_("Two-factor configured"))
    def has_two_factor(self, obj: UserSecret) -> bool:
        """Reports whether a TOTP secret is present."""
        return bool(obj.otp_secret_key)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Hardened central administration for user accounts."""

    inlines = (UserProfileInline, UserSecretInline)

    list_display = (
        "email",
        "username",
        "is_verified",
        "is_suspended",
        "get_role",
        "is_staff",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "is_verified",
        "profile__role",
    )

    search_fields = ("email", "username")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (
            _("Personal information"),
            {"fields": ("first_name", "last_name", "last_ip_address")},
        ),
        (
            _("Permissions and status"),
            {
                "fields": (
                    "is_active",
                    "is_verified",
                    "is_suspended",
                    "two_factor_enabled",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Audit"),
            {
                "fields": (
                    "date_joined",
                    "last_login",
                    "failed_login_attempts",
                    "password_changed_at",
                )
            },
        ),
    )

    readonly_fields = (
        "date_joined",
        "last_login",
        "last_ip_address",
        "failed_login_attempts",
        "password_changed_at",
    )

    def get_role(self, obj):
        return obj.profile.role if hasattr(obj, "profile") else "-"

    get_role.short_description = _("Role")

    def has_delete_permission(self, request, obj=None):
        """Blocks destructive deletion; anonymisation is the sanctioned path."""
        return False
