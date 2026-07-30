from typing import Any

from rest_framework import serializers

from ..models import UserSecret

# Logical field names, without the `_encrypted` suffix. Each is written through
# `UserSecret.set_sensitive_data`, which encrypts it and derives a blind index
# where the model declares one.
SENSITIVE_FIELDS = ("dni", "phone_number", "date_of_birth")


class UserSecretSerializer(serializers.Serializer):
    """Writes identity data into the encrypted vault.

    Every field is write-only: a stored value must never be readable back
    through the API, only overwritten. The serializer therefore exposes no
    output beyond a confirmation.

    This replaces an earlier version accepting exchange API credentials
    (ADR-0005). Those columns named a specific third party in what is meant to
    be a generic template, and they were the only fields this endpoint served —
    leaving the project's most heavily protected write with no purpose for most
    consumers.
    """

    dni = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=64
    )
    phone_number = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=32
    )
    date_of_birth = serializers.DateField(write_only=True, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Rejects a request that would write nothing.

        Args:
            attrs (dict[str, Any]): The validated field values.

        Returns:
            dict[str, Any]: The same values, unchanged.

        Raises:
            serializers.ValidationError: When no known field was supplied.
        """
        if not any(field in attrs for field in SENSITIVE_FIELDS):
            raise serializers.ValidationError(
                f"Provide at least one of: {', '.join(SENSITIVE_FIELDS)}."
            )
        return attrs

    def update(self, instance: UserSecret, validated_data: dict[str, Any]) -> UserSecret:
        """Encrypts each supplied value and records an audit entry per field.

        Args:
            instance (UserSecret): The vault being written to.
            validated_data (dict[str, Any]): Fields to store.

        Returns:
            UserSecret: The saved instance.
        """
        from django.apps import apps

        audit_model = apps.get_model("users", "UserSecretAudit")
        ip_address = self._client_ip()
        touched: list[str] = []

        for field in SENSITIVE_FIELDS:
            if field not in validated_data:
                continue

            raw = validated_data[field]
            # A DateField arrives as a date object; the vault stores strings.
            instance.set_sensitive_data(field, str(raw) if raw != "" else None)
            touched.append(field)

            audit_model.objects.create(
                user=instance.user,
                field_affected=field,
                action_type="UPDATE",
                ip_address=ip_address,
            )

        instance.save()
        self._touched = touched
        return instance

    def _client_ip(self) -> str | None:
        """Extracts the caller's IP, preferring the first proxy hop.

        Returns:
            str | None: The client address, or None outside a request context.
        """
        request = self.context.get("request")
        if not request:
            return None

        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
