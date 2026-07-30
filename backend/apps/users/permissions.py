from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from . import step_up


class IsVerified(permissions.BasePermission):
    """
    Grants access only to users who have successfully verified their account.

    Applies to critical actions such as trading or API key configuration.
    """

    message = "You must verify your account to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.is_verified
        )


class IsPremiumUser(permissions.BasePermission):
    """
    Grants access only to users with 'premium' role or higher (staff/superuser).
    """

    message = "This functionality requires an active Premium subscription."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        # Superusers or Staff bypass role restrictions
        if request.user.is_staff or request.user.is_superuser:
            return True

        return (
            hasattr(request.user, "profile") and request.user.profile.role == "premium"
        )


class RequiresStepUp(permissions.BasePermission):
    """Blocks sensitive endpoints without a recent re-authentication.

    Resolution is delegated to `step_up.is_granted`, which checks the session
    and the shared cache in turn (ADR-0002). Reading only the session, as this
    class previously did, made every gated endpoint unreachable for
    bearer-token clients, which never have one.
    """

    message = "This action requires a recent security validation (Step-Up Auth)."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        return step_up.is_granted(request, request.user)


class IsOwner(permissions.BasePermission):
    """
    Object-level permission to ensure users can only modify their own data.
    """

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        # If the object is the user themselves
        if hasattr(obj, "id") and obj.id == request.user.id:
            return True

        # If the object has a FK to the user (e.g., Profile, UserSecret)
        if hasattr(obj, "user"):
            return obj.user == request.user

        return False
