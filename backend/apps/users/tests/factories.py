"""Model factories for the users app.

Built on ``factory_boy``, which ships in ``requirements.txt``. Users are created
through ``CustomUserManager.create_user`` rather than a bare ``Model(**kwargs)``
so that email normalisation, password hashing and the ``post_save`` receiver
that provisions ``UserProfile`` and ``UserSecret`` all run exactly as they do in
production.
"""

from typing import Any

import factory
from django.contrib.auth import get_user_model

User = get_user_model()

DEFAULT_PASSWORD = "StrongPassword123!"


class UserFactory(factory.django.DjangoModelFactory):
    """Creates a live, non-anonymised user with its satellite records."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.test")
    username = factory.Sequence(lambda n: f"user{n}")

    @classmethod
    def _create(cls, model_class: type, *args: Any, **kwargs: Any) -> Any:
        """Routes creation through the manager instead of the default path.

        Args:
            model_class (type): The user model being built.
            *args (Any): Positional arguments forwarded by factory_boy.
            **kwargs (Any): Declared attributes, optionally including
                ``password``.

        Returns:
            Any: The persisted user instance.
        """
        password = kwargs.pop("password", DEFAULT_PASSWORD)
        return model_class.objects.create_user(password=password, **kwargs)


class VerifiedUserFactory(UserFactory):
    """A user that has already completed account verification."""

    is_verified = True


class StaffUserFactory(VerifiedUserFactory):
    """A verified user with admin-site access."""

    is_staff = True
    is_superuser = True
