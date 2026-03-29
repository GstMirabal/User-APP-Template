import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestUserAPI:
    """
    Tactical test suite for the User API.
    """

    def test_user_registration_success(self, client):
        """Validate successful registration and automatic Profile/Secret creation."""
        url = reverse("users:user-register")
        data = {
            "email": "tester@user-app-template.com",
            "username": "testerbot",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email=data["email"]).exists()

        user = User.objects.get(email=data["email"])
        assert hasattr(user, "profile")
        assert hasattr(user, "secrets")
        assert user.is_verified is False

    def test_user_registration_password_mismatch(self, client):
        """Validate failure if passwords do not match."""
        url = reverse("users:user-register")
        data = {
            "email": "bad@user-app-template.com",
            "username": "baduser",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }

        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password_confirm" in response.data

    def test_user_verification_flow(self, client):
        """Test full OTP flow: generation, mock send, and validation."""
        register_url = reverse("users:user-register")
        client.post(
            register_url,
            {
                "email": "verify@user-app-template.com",
                "username": "verifyuser",
                "password": "StrongPassword123!",
                "password_confirm": "StrongPassword123!",
            },
        )

        user = User.objects.get(email="verify@user-app-template.com")
        otp = user.secrets.api_key_binance_encrypted.split(":")[1]

        verify_url = reverse("users:user-verify")
        response = client.post(
            verify_url, {"email": "verify@user-app-template.com", "code": otp}
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_verified is True

    def test_sensitive_endpoints_require_verification_and_stepup(self, client):
        """Validate that secrets endpoints require verification and Step-Up."""
        user = User.objects.create_user(
            email="secure@user-app-template.com",
            username="secure",
            password="StrongPassword123!",
            is_verified=True,
        )
        client.force_login(user)

        url = reverse("users:user-secrets")
        # Should fail with 403 because no Step-Up session exists yet (SessionAuth)
        response = client.patch(
            url, {"api_key_binance_encrypted": "test"}, content_type="application/json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_step_up_reauth_flow(self, client):
        """Test the reauth flow to gain Step-Up access."""
        password = "StrongPassword123!"
        user = User.objects.create_user(
            email="reauth@user-app-template.com",
            username="reauth_user",
            password=password,
            is_verified=True,
        )
        client.force_login(user)

        reauth_url = reverse("users:user-reauth")
        response = client.post(
            reauth_url, {"password": password}, content_type="application/json"
        )
        assert response.status_code == status.HTTP_200_OK

        # Now secrets should be accessible
        url = reverse("users:user-secrets")
        response = client.patch(
            url, {"api_key_binance_encrypted": "xyz"}, content_type="application/json"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_2fa_anti_replay(self, client):
        """Validate TOTP token anti-replay protection."""
        user = User.objects.create_user(
            email="2fa_replay@user-app-template.com",
            username="2fa_user",
            password="StrongPassword123!",
            is_verified=True,
        )
        secret = pyotp.random_base32()
        user.secrets.otp_secret_key = secret
        user.secrets.save()

        totp = pyotp.TOTP(secret)
        token = totp.now()

        client.force_login(user)
        # Using hardcoded path to avoid NoReverseMatch issues with nested router actions during test stabilization
        activate_url = "/api/v1/users/me/2fa/activate/"

        # 1. First use: Success
        response = client.post(
            activate_url, {"token": token}, content_type="application/json"
        )
        assert response.status_code == status.HTTP_200_OK

        # 2. Replay usage: Failure
        response = client.post(
            activate_url, {"token": token}, content_type="application/json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
