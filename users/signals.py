from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, UserSecret

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)

# `get_user_model()` returns the model *class*, not an instance. The annotation
# read `AbstractUser` until Sprint #004 and was simply false.
User: type[AbstractUser] = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile_and_secrets(
    sender: type[AbstractUser],
    instance: AbstractUser,
    created: bool,
    **kwargs: Any,
) -> None:
    """Provisions the profile and secret vault for a newly created user.

    Runs atomically: an account without its satellite rows would fail on the
    first request that touches `user.profile` or `user.secrets`, so a failure
    here rolls the user creation back rather than leaving a half-built account.

    `_registration_metadata` is read off the instance because a `post_save`
    receiver has no other way to see data that is not a model field. The
    manager sets it before saving.

    Args:
        sender (type[AbstractUser]): The User model class.
        instance (AbstractUser): The created user instance.
        created (bool): Flag indicating if this is a new record.
        **kwargs (Any): Additional signal keywords.

    Raises:
        Exception: Re-raised after logging, so the transaction rolls back.
    """
    if created:
        try:
            with transaction.atomic():
                # Capture temporary registration metadata (if provided during creation)
                registration_metadata: dict[str, Any] = getattr(
                    instance, "_registration_metadata", {}
                )

                # Determine initial language preference
                initial_language: str = registration_metadata.get(
                    "language_code", "en-us"
                )

                # 1. Create UserProfile
                UserProfile.objects.create(
                    user=instance,
                    registration_data=registration_metadata,
                    language_code=initial_language,
                )

                # 2. Create UserSecret (Empty vault)
                UserSecret.objects.create(user=instance)

        except Exception:
            # The rollback takes the user row with it, so without this record
            # the only trace is a registration that returned an error and left
            # nothing behind. `agents.md §1` requires the log, and catching
            # only to re-raise — as this did until Sprint #004 — satisfied
            # neither the rule nor a reader.
            logger.exception(
                "Failed to provision profile and secret vault for user %s; "
                "rolling back the account creation",
                instance.pk,
            )
            raise
