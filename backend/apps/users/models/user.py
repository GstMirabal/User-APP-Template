import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from ..managers import AuditManager, CustomUserManager

class Address(models.Model):
    """Reusable model for storing postal addresses."""
    street_address = models.CharField(_("Street address"), max_length=255)
    address_line_2 = models.CharField(
        _("Address line 2"), max_length=255, blank=True, null=True,
        help_text=_("Apartment, unit, building, floor, etc.")
    )
    city = models.CharField(_("City"), max_length=100)
    postal_code = models.CharField(_("Postal code"), max_length=20)
    country = models.CharField(_("Country"), max_length=100)
    state_province = models.CharField(_("State / Province"), max_length=100, blank=True, null=True)

    class Meta:
        app_label = "users"
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self) -> str:
        return f"{self.street_address}, {self.city}"


class User(AbstractUser):
    """Custom User model for User-APP-Template."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("Email address"), unique=True)
    username = models.CharField(
        _("Username"),
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer."),
        error_messages={"unique": _("A user with that username already exists.")},
    )

    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    last_ip_address = models.GenericIPAddressField(_("Last IP address"), blank=True, null=True)
    password_changed_at = models.DateTimeField(_("Last password change"), blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(_("Failed login attempts"), default=0)
    is_anonymized = models.BooleanField(_("Is anonymized"), default=False)
    deleted_at = models.DateTimeField(_("Deleted at"), blank=True, null=True, default=None)
    is_verified = models.BooleanField(_("Email verified"), default=False)
    two_factor_enabled = models.BooleanField(_("2FA active"), default=False)
    is_suspended = models.BooleanField(_("Is suspended"), default=False)

    suspension_reason = models.TextField(_("Suspension reason"), blank=True, null=True)

    billing_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="users_billing", verbose_name=_("Billing address")
    )
    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="users_shipping", verbose_name=_("Shipping address")
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()
    audit_objects = AuditManager()

    class Meta:
        app_label = "users"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
        ]

    def __str__(self) -> str:
        return self.email
