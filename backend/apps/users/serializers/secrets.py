from typing import Any

from rest_framework import serializers

from ..models import UserSecret


class UserSecretSerializer(serializers.ModelSerializer):
    """Serializer for managing highly sensitive user data and exchange keys.

    All sensitive fields MUST be explicitly write-only.
    """

    api_key_binance_encrypted = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    api_secret_binance_encrypted = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )

    class Meta:
        model = UserSecret
        fields = [
            "api_key_binance_encrypted",
            "api_secret_binance_encrypted",
        ]

    def update(
        self, instance: UserSecret, validated_data: dict[str, Any]
    ) -> UserSecret:
        """Encrypt secrets and log audit trail."""
        from django.apps import apps

        UserSecretAudit = apps.get_model("users", "UserSecretAudit")

        request = self.context.get("request")
        ip_address = None
        if request:
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(",")[0]
            else:
                ip_address = request.META.get("REMOTE_ADDR")

        api_key = validated_data.pop("api_key_binance_encrypted", None)
        api_secret = validated_data.pop("api_secret_binance_encrypted", None)

        if api_key is not None:
            instance.set_sensitive_data("api_key_binance", api_key)
            UserSecretAudit.objects.create(
                user=instance.user,
                field_affected="api_key_binance",
                action_type="UPDATE",
                ip_address=ip_address,
            )
        if api_secret is not None:
            instance.set_sensitive_data("api_secret_binance", api_secret)
            UserSecretAudit.objects.create(
                user=instance.user,
                field_affected="api_secret_binance",
                action_type="UPDATE",
                ip_address=ip_address,
            )

        return super().update(instance, validated_data)
