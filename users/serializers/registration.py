import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()
logger = logging.getLogger(__name__)


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer purely focused on user creation with strict validation."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    language_code = serializers.CharField(
        write_only=True, required=False, max_length=10, default="en-us"
    )

    class Meta:
        model = User
        fields = ["email", "username", "password", "password_confirm", "language_code"]

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Ensures password confirmation matches."""
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "The passwords do not match."}
            )
        return data

    def create(self, validated_data: dict[str, Any]) -> Any:
        """Safely creates a mapped User through the UserManager.

        `language_code` reaches the profile through `_registration_metadata`,
        which the `post_save` receiver reads. It was accepted and dropped here
        until Sprint #004: the request succeeded with `201` while the caller's
        preference was silently replaced by the default.

        Args:
            validated_data (dict[str, Any]): Validated registration payload.

        Returns:
            Any: The created user instance.
        """
        validated_data.pop("password_confirm")

        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            registration_metadata={
                "language_code": validated_data.get("language_code", "en-us")
            },
        )

        logger.info("Registered new user via API: %s", user.pk)
        return user
