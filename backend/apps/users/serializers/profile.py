from rest_framework import serializers

from ..models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for managing user preferences and profile visual data."""

    class Meta:
        model = UserProfile
        fields = [
            "role",
            "timezone",
            "preferred_currency",
            "language_code",
            "avatar",
            "bio",
            "email_notifications_enabled",
        ]
        read_only_fields = ["role"]
