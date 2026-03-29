from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class IsVerified(permissions.BasePermission):
    """
    Grants access only to users who have successfully verified their account.
    
    Applies to critical actions such as trading or API key configuration.
    """

    message = "You must verify your account to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_verified)


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

        return hasattr(request.user, "profile") and request.user.profile.role == "premium"


from django.utils import timezone
from datetime import timedelta

class RequiresStepUp(permissions.BasePermission):
    """
    Blocks access to highly sensitive endpoints unless the user has 
    re-authenticated (Step-Up) within the last 5 minutes.
    """
    message = "This action requires a recent security validation (Step-Up Auth)."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
            
        # Retrieve the Step-Up timestamp (stored in session by login/reauth endpoint)
        step_up_at = request.session.get('step_up_timestamp')
        
        if not step_up_at:
            return False
            
        # Validate that Step-Up occurred within the last 5 minutes
        last_auth = timezone.datetime.fromisoformat(step_up_at)
        if timezone.now() > last_auth + timedelta(minutes=5):
            return False
            
        return True


class IsOwner(permissions.BasePermission):
    """
    Object-level permission to ensure users can only modify their own data.
    """


    def has_object_permission(self, request: Request, view: APIView, obj: any) -> bool:
        # If the object is the user themselves
        if hasattr(obj, "id") and obj.id == request.user.id:
            return True
        
        # If the object has a FK to the user (e.g., Profile, UserSecret)
        if hasattr(obj, "user"):
            return obj.user == request.user
            
        return False
