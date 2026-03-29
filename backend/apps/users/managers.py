from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.contrib.auth.base_user import BaseUserManager
from django.db import models, transaction
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


class SoftDeleteQuerySet(models.QuerySet):
    """Custom QuerySet to implement soft deletion and anonymization logic."""

    def alive(self) -> QuerySet:
        """Returns active users (deleted_at IS NULL)."""
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> QuerySet:
        """Returns deleted users (deleted_at IS NOT NULL)."""
        return self.filter(deleted_at__isnull=False)

    def anonymized(self) -> QuerySet:
        """Returns anonymized users."""
        return self.filter(is_anonymized=True)

    def delete(self) -> int:
        """Performs a soft delete.

        Propagates the deletion timestamp to related UserProfile and UserSecret models.

        Returns:
            int: The number of rows updated in the main model.
        """
        now = timezone.now()
        with transaction.atomic():
            # Propagation to related models (Lazy loading to avoid circular imports)
            UserProfile = apps.get_model('users', 'UserProfile')
            UserSecret = apps.get_model('users', 'UserSecret')

            # Update satellite tables
            UserProfile.objects.filter(user__in=self).update(deleted_at=now)
            UserSecret.objects.filter(user__in=self).update(deleted_at=now)

            # Update users
            return self.update(deleted_at=now)

    def restore(self) -> int:
        """Restores deleted users by clearing deleted_at.

        Does not allow restoration if the user is anonymized.

        Returns:
            int: The number of rows restored.
        """
        # Filter non-anonymized records for restoration
        restorable: QuerySet = self.filter(is_anonymized=False)

        with transaction.atomic():
            UserProfile = apps.get_model('users', 'UserProfile')
            UserSecret = apps.get_model('users', 'UserSecret')

            UserProfile.objects.filter(
                user__in=restorable).update(deleted_at=None)
            UserSecret.objects.filter(
                user__in=restorable).update(deleted_at=None)

            return restorable.update(deleted_at=None)

    def anonymize(self) -> None:
        """Performs destructive PII anonymization.

        1. Marks is_anonymized = True.
        2. Generates a unique technical identity based on UUID.
        3. Clears PII in User, UserProfile, and UserSecret.
        4. Executes a soft delete at the end.
        """
        with transaction.atomic():
            for user in self:
                if user.is_anonymized:
                    continue

                # 1. Technical Identity
                anon_id: str = f"anon_{user.id}"
                anon_email: str = f"{anon_id}@user-app-template.internal"

                user.is_anonymized = True
                user.email = anon_email
                user.username = anon_email  # Username = Email in this system
                user.first_name = "Anonymized"
                user.last_name = "User"
                user.set_unusable_password()

                # 2. UserProfile cleanup
                if hasattr(user, 'profile'):
                    profile = user.profile
                    profile.bio = "Anonymized Data"
                    profile.avatar = None
                    profile.marketing_consent = False
                    profile.save()

                # 3. UserSecret cleanup
                if hasattr(user, 'secrets'):
                    secrets = user.secrets
                    secrets.dni_encrypted = None
                    secrets.dni_index = None
                    secrets.date_of_birth_encrypted = None
                    secrets.phone_number_encrypted = None
                    secrets.phone_number_index = None
                    secrets.api_key_binance_encrypted = None
                    secrets.api_key_binance_index = None
                    secrets.api_secret_binance_encrypted = None
                    secrets.otp_secret_key = None
                    secrets.otp_recovery_codes = None
                    secrets.save()

                user.save()

            # 4. Final Soft Delete
            self.delete()

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """Performs a real physical deletion (SQL DELETE)."""
        return super().delete()


class CustomUserManager(BaseUserManager.from_queryset(SoftDeleteQuerySet)):
    """Custom user manager supporting email login and soft deletion."""
    use_in_migrations = True

    def _create_user(self, email: str, username: str, password: str | None, **extra_fields: Any) -> Any:
        """Internal method to create and save a user. Satellite models are handled by signals."""
        if not email:
            raise ValueError('The email must be set')
        if not username:
            raise ValueError('The username must be set')

        email = self.normalize_email(email).lower()
        
        with transaction.atomic():
            user = self.model(email=email, username=username, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
            return user



    def create_user(self, email: str, username: str, password: str | None = None, **extra_fields: Any) -> Any:
        """Creates a standard user."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email: str, username: str, password: str | None = None, **extra_fields: Any) -> Any:
        """Creates a superuser with strict permission validation."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, username, password, **extra_fields)

    def get_queryset(self) -> QuerySet:
        """Overrides get_queryset to use SoftDeleteQuerySet.

        Hides deleted/anonymized records by default.
        """
        return super().get_queryset().alive()


class AuditQuerySet(SoftDeleteQuerySet):
    """Audit QuerySet that blocks physical deletion."""

    def hard_delete(self) -> None:
        """Blocks physical deletion to preserve historical integrity.

        Raises:
            NotImplementedError: Always, as hard delete is prohibited.
        """
        raise NotImplementedError(
            "Hard delete is not allowed in AuditManager to preserve historical data integrity."
        )


class AuditManager(models.Manager):
    """Audit Manager: Total access including deleted and anonymized records."""

    def get_queryset(self) -> QuerySet:
        """Returns the full QuerySet without visibility filters."""
        return AuditQuerySet(self.model, using=self._db)
