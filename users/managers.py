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
            UserProfile = apps.get_model("users", "UserProfile")
            UserSecret = apps.get_model("users", "UserSecret")

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
            UserProfile = apps.get_model("users", "UserProfile")
            UserSecret = apps.get_model("users", "UserSecret")

            UserProfile.objects.filter(user__in=restorable).update(deleted_at=None)
            UserSecret.objects.filter(user__in=restorable).update(deleted_at=None)

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

                # 1. Technical Identity. `.invalid` is reserved by RFC 2606
                # precisely so it can never resolve, and it does not stamp this
                # app's name onto a host's permanent records — the domain
                # written here outlives the row.
                anon_id: str = f"anon_{user.id}"
                anon_email: str = f"{anon_id}@anonymized.invalid"

                user.is_anonymized = True
                user.email = anon_email
                user.username = anon_email  # Username = Email in this system
                user.first_name = "Anonymized"
                user.last_name = "User"
                user.set_unusable_password()

                # 2. UserProfile cleanup. `registration_data` is a free-form
                # JSONField a host is invited to fill (the post_save receiver
                # reads `_registration_metadata` for exactly that), so leaving
                # it would let arbitrary personal data survive an operation
                # whose entire purpose is erasing it. `last_activity_at` goes
                # too: a behavioural timestamp is still data about a person.
                if hasattr(user, "profile"):
                    profile = user.profile
                    profile.bio = "Anonymized Data"
                    profile.avatar = None
                    profile.marketing_consent = False
                    profile.registration_data = {}
                    profile.last_activity_at = None
                    profile.save()

                # 3. UserSecret cleanup
                if hasattr(user, "secrets"):
                    secrets = user.secrets
                    secrets.dni_encrypted = None
                    secrets.dni_index = None
                    secrets.date_of_birth_encrypted = None
                    secrets.phone_number_encrypted = None
                    secrets.phone_number_index = None
                    secrets.verification_otp_encrypted = None
                    secrets.verification_otp_expires_at = None
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
    """Custom user manager supporting email login and soft deletion.

    `get_queryset()` hides soft-deleted rows, so this manager deliberately does
    NOT set `use_in_migrations`. It did until Sprint #004, which meant a data
    migration reaching for `User.objects` silently skipped every deleted row —
    a filtered manager and migration use are a pairing Django's documentation
    warns against. Migrations that need every row use `audit_objects`.
    """

    def _create_user(
        self,
        email: str,
        username: str,
        password: str | None,
        registration_metadata: dict[str, Any] | None = None,
        **extra_fields: Any,
    ) -> Any:
        """Internal method to create and save a user.

        Satellite models are provisioned by the `post_save` receiver, which
        reads `_registration_metadata` off the instance. That attribute has to
        be set before `save()`, so it is accepted here rather than left to a
        caller that never gets to touch the instance in between.

        Args:
            email (str): Login identifier; normalised and lowercased.
            username (str): Display identifier.
            password (str | None): Raw password, or None for an unusable one.
            registration_metadata (dict[str, Any] | None): Context stored on
                the new profile, such as the caller's language preference.
            **extra_fields (Any): Further model fields.

        Returns:
            Any: The created user instance.

        Raises:
            ValueError: If email or username is empty.
        """
        if not email:
            raise ValueError("The email must be set")
        if not username:
            raise ValueError("The username must be set")

        email = self.normalize_email(email).lower()

        with transaction.atomic():
            user = self.model(email=email, username=username, **extra_fields)
            user._registration_metadata = registration_metadata or {}
            user.set_password(password)
            user.save(using=self._db)
            return user

    def create_user(
        self,
        email: str,
        username: str,
        password: str | None = None,
        registration_metadata: dict[str, Any] | None = None,
        **extra_fields: Any,
    ) -> Any:
        """Creates a standard user.

        Args:
            email (str): Login identifier.
            username (str): Display identifier.
            password (str | None): Raw password.
            registration_metadata (dict[str, Any] | None): Context stored on
                the new profile.
            **extra_fields (Any): Further model fields.

        Returns:
            Any: The created user instance.
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(
            email, username, password, registration_metadata, **extra_fields
        )

    def create_superuser(
        self,
        email: str,
        username: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> Any:
        """Creates a superuser with strict permission validation."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

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
