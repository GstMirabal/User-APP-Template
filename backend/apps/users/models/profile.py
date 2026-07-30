from django.db import models
from django.utils.translation import gettext_lazy as _

from .user import User


class UserProfile(models.Model):
    """Preferences, presentation data and legal consent for a user.

    Created automatically by the `post_save` receiver on `User`, inside the
    same transaction, so a live user always has one.
    """

    class UserRole(models.TextChoices):
        FREE = "free", _("Free")
        PREMIUM = "premium", _("Premium")
        ADMIN = "admin", _("Admin")

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
    )
    role = models.CharField(
        _("User role"),
        max_length=15,
        choices=UserRole.choices,
        default=UserRole.FREE,
    )

    # Preferences
    timezone = models.CharField(_("Time zone"), max_length=100, default="UTC")
    preferred_currency = models.CharField(
        _("Preferred currency"), max_length=10, default="USD"
    )
    language_code = models.CharField(_("Language"), max_length=10, default="en-us")
    avatar = models.ImageField(_("Avatar"), upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(_("Biography"), blank=True, null=True)
    email_notifications_enabled = models.BooleanField(
        _("Email notifications enabled"), default=True
    )

    # Legal consent
    accepted_terms_at = models.DateTimeField(
        _("Terms accepted at"), blank=True, null=True
    )
    accepted_privacy_policy_at = models.DateTimeField(
        _("Privacy policy accepted at"), blank=True, null=True
    )
    marketing_consent = models.BooleanField(
        _("Marketing consent"), default=False
    )
    registration_data = models.JSONField(
        _("Registration metadata"), default=dict, blank=True
    )
    last_activity_at = models.DateTimeField(
        _("Last activity at"), blank=True, null=True
    )
    deleted_at = models.DateTimeField(
        _("Deleted at"), blank=True, null=True, default=None
    )

    class Meta:
        app_label = "users"
        verbose_name = _("User profile")
        verbose_name_plural = _("User profiles")

    def __str__(self) -> str:
        return f"Profile for {self.user.username}"
