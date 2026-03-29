from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, UserSecret

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User: AbstractUser = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile_and_secrets(
    sender: type[AbstractUser],
    instance: AbstractUser,
    created: bool,
    **kwargs: Any,
) -> None:
    """Post-save signal to automatically create UserProfile and UserSecret.

    Executed after a User instance is saved. If 'created' is True, it atomicallly
    initializes the satellite models and schedules post-transaction tasks.

    Args:
        sender (Type[AbstractUser]): The User model class.
        instance (AbstractUser): The created user instance.
        created (bool): Flag indicating if this is a new record.
        **kwargs (Any): Additional signal keywords.

    Raises:
        Exception: If satellite creation fails, triggering an atomic rollback.
    """
    if created:
        try:
            with transaction.atomic():
                # Capture temporary registration metadata (if provided during creation)
                registration_metadata: dict[str, Any] = getattr(
                    instance, '_registration_metadata', {}
                )

                # Determine initial language preference
                initial_language: str = registration_metadata.get(
                    'language_code', 'en-us'
                )

                # 1. Create UserProfile
                UserProfile.objects.create(
                    user=instance,
                    registration_data=registration_metadata,
                    language_code=initial_language,
                )

                # 2. Create UserSecret (Empty vault)
                UserSecret.objects.create(user=instance)

                # 3. Post-transaction processes (Welcome Emails, etc.)
                def send_welcome_email() -> None:
                    """Logic for sending a welcome email via Celery/Background task."""
                    # Example: send_welcome_email_task.delay(instance.id)
                    pass

                transaction.on_commit(send_welcome_email)

        except Exception as e:
            # Atomic rollback is automatic, but we re-raise for awareness.
            raise e
