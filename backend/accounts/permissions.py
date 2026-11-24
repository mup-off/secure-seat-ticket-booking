"""Access control enforced on the server (plan, Phase 2: Elevation of privilege).
Hiding a button in the React app is never treated as protection."""
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class IsBuyer(BasePermission):
    message = "Only buyer accounts can do this."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "buyer")


class IsOrganizerWith2FA(BasePermission):
    """Organizer role AND two-step verification set up AND passed in this session."""

    message = "Only organizer accounts can do this."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == "organizer"):
            return False
        if not user.totp_enabled:
            raise PermissionDenied({"detail": "Set up two-step verification first.", "code": "mfa_setup_required"})
        if not request.session.get("mfa"):
            raise PermissionDenied({"detail": "Two-step verification required.", "code": "mfa_required"})
        return True
