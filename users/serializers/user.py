from django.contrib.auth import get_user_model
from rest_framework import serializers

from .profile import UserProfileSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for reading user data."""

    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "is_verified",
            "profile",
            "failed_login_attempts",
            "date_joined",
        ]
        read_only_fields = ["id", "is_verified", "failed_login_attempts", "date_joined"]
