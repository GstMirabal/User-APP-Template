import logging

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import GenericViewSet

from . import step_up
from .defaults import step_up_window_seconds
from .permissions import IsVerified, RequiresStepUp
from .serializers import (
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSecretSerializer,
    UserSerializer,
)
from .services import VerificationService

logger = logging.getLogger(__name__)
User = get_user_model()


class UserViewSet(GenericViewSet):
    """ViewSet to orchestrate Account Registration and Profile Management."""

    queryset = User.objects.select_related("profile", "secrets").all()

    def get_throttles(self):
        """Override to apply sensitive throttling for specific actions."""
        if self.action in ["register", "verify", "reauth"]:
            self.throttle_scope = "sensitive"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_permissions(self):
        """Override to map permissions based on exact endpoint action."""
        if self.action in ["register", "verify"]:
            return [AllowAny()]

        if self.action == "reauth":
            return [IsAuthenticated()]

        # High-sensitivity actions requiring verification + Step-Up Auth
        if self.action in ["secrets", "anonymize_account"]:
            return [IsAuthenticated(), IsVerified(), RequiresStepUp()]

        return [IsAuthenticated()]

    def get_serializer_class(self):
        """Return dynamic serializers depending on caller intent."""
        if self.action == "register":
            return UserRegistrationSerializer
        if self.action == "secrets":
            return UserSecretSerializer
        if self.action == "profile":
            return UserProfileSerializer
        return UserSerializer

    @action(detail=False, methods=["post"], url_path="me/reauth")
    def reauth(self, request: Request) -> Response:
        """Validate the password to gain Step-Up access.

        Goes through ``django.contrib.auth.authenticate`` rather than
        ``user.check_password``. ``AxesBackend`` sits first in
        ``AUTHENTICATION_BACKENDS`` and only counts attempts that pass through
        it, so the direct call left this endpoint — a password oracle for an
        already-authenticated session — outside brute-force protection
        entirely. The ``sensitive`` throttle remains as a second layer.
        """
        password = request.data.get("password")
        if not password:
            return Response(
                {"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        authenticated = authenticate(
            request=request,
            username=request.user.get_username(),
            password=password,
        )

        if authenticated is None or authenticated.pk != request.user.pk:
            logger.warning(
                "Failed step-up re-authentication for user %s", request.user.pk
            )
            return Response(
                {"error": "Incorrect password."}, status=status.HTTP_403_FORBIDDEN
            )

        step_up.grant(request, request.user)
        window_minutes = step_up_window_seconds() // 60

        return Response(
            {
                "detail": (
                    "Step-Up validation successful. Access granted for "
                    f"{window_minutes} minutes."
                )
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request: Request) -> Response:
        """Create an account and issue its email verification code."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Trigger mock verification flow
        VerificationService.initialize_verification_flow(user)

        logger.info("Registration completed for user %s", user.pk)

        return Response(
            {
                "detail": (
                    "Account created. A verification code has been issued; "
                    "follow the instructions sent to your registered address."
                ),
                "user_id": user.id,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="verify")
    def verify(self, request: Request) -> Response:
        """Verify user account with OTP."""
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response(
                {"error": "Both 'email' and 'code' must be provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND
            )

        if VerificationService.verify_account(user, code):
            return Response(
                {"detail": "Account verified! You now have full access."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Invalid verification code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request: Request) -> Response:
        """Fetch or update the current authenticated user's core info."""
        user = request.user

        if request.method == "PATCH":
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["patch"], url_path="me/profile")
    def profile(self, request: Request) -> Response:
        """Updates nested profile preferences separately."""
        user = request.user

        # UserProfile must exist, post_save guarantees atomic synthesis.
        serializer = UserProfileSerializer(
            user.profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["patch"], url_path="me/secrets")
    def secrets(self, request: Request) -> Response:
        """Writes identity data into the encrypted vault.

        Gated by verification plus step-up re-authentication. Every field is
        write-only, so a stored value can be overwritten but never read back.
        """
        user = request.user

        serializer = UserSecretSerializer(
            user.secrets, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Sensitive data stored, encrypted at rest."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="me/2fa/setup")
    def setup_2fa(self, request: Request) -> Response:
        """
        Generates a secret and URI to configure Google Authenticator.
        """
        user = request.user

        # Setup Guard: Prevent overwriting active 2FA
        if user.two_factor_enabled:
            return Response(
                {"error": "2FA is already active. Deactivate it first to reconfigure."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = VerificationService.setup_2fa(user)

        return Response(
            {
                "detail": (
                    "Scan this URI in your authenticator app and SAVE your "
                    "recovery codes safely."
                ),
                "otp_uri": data["otp_uri"],
                "secret": data["secret"],
                "recovery_codes": data["recovery_codes"],
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="me/2fa/activate")
    def activate_2fa(self, request: Request) -> Response:
        """
        Verifies the first TOTP token to activate 2FA on the account.
        """
        user = request.user
        token = request.data.get("token")

        if not token:
            return Response(
                {"error": "6-digit token must be provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if VerificationService.verify_2fa(user, token):
            # Update 2FA flag on User model
            user.two_factor_enabled = True
            user.save(update_fields=["two_factor_enabled"])

            return Response(
                {"detail": "Two-Factor Authentication (2FA) activated successfully!"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Invalid or expired 2FA token."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"], url_path="me/anonymize")
    def anonymize_account(self, request: Request) -> Response:
        """Request irreversible account anonymization following GDPR compliance.

        Uses the Manager's SoftDeletion strategy to mutate personal traits.
        """
        user = request.user
        confirmation = request.data.get("confirmation", "").strip().lower()

        if confirmation != f"delete {user.email}":
            raise PermissionDenied(
                f"Incorrect confirmation. Please type: 'delete {user.email}'"
            )

        logger.warning(
            "Irreversible anonymisation started for user %s", user.pk
        )

        # Extract the user into a specific single-object QuerySet
        # that utilizes the SoftDeleteQuerySet to trigger the Manager.
        qs = User.objects.filter(id=user.id)
        qs.anonymize()

        return Response(
            {
                "detail": (
                    "Account has been successfully anonymized and closed. "
                    "Session will be terminated."
                )
            },
            status=status.HTTP_200_OK,
        )
