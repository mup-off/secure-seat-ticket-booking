"""Sign-up, login with account lockout, organizer two-step verification, logout."""
import logging
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import F
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit.services import record
from core.logging import alert

from . import totp
from .models import User
from .serializers import CodeSerializer, LoginSerializer, RegisterSerializer, user_data

logger = logging.getLogger("secureseat")

# Used when the email is unknown, so a failed login takes the same time either way
# and doesn't reveal which emails have accounts.
_DUMMY_HASH = make_password("not-a-real-password-just-for-timing")
GENERIC_LOGIN_ERROR = "Email or password is incorrect."
PENDING_MFA_SECONDS = 5 * 60


def _client_ip(request):
    return request.META.get("REMOTE_ADDR")


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(APIView):
    """GET sets the CSRF cookie and returns the signed-in user (or null)."""

    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user if request.user.is_authenticated else None
        return Response({"user": user_data(user, request.session) if user else None})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.create_user(**s.validated_data)
        record(user, "user.registered", f"user:{user.id}", role=user.role)
        login(request, user)  # also gives the session a new ID
        request.session["mfa"] = False
        return Response({"user": user_data(user, request.session)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]  # per-IP limit
    throttle_scope = "login"

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        # Always run the password hash, even for unknown emails (timing).
        ok = check_password(s.validated_data["password"], user.password if user else _DUMMY_HASH)

        if user and user.is_locked():
            logger.warning("Login attempt on locked account", extra={"data": {"user": user.id, "ip": _client_ip(request)}})
            return Response({"detail": "Too many failed attempts. This account is locked for a few minutes."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        if not user or not ok or not user.is_active:
            if user:
                self._count_failure(user, request)
            logger.warning("Failed login", extra={"data": {"ip": _client_ip(request), "known_user": bool(user)}})
            return Response({"detail": GENERIC_LOGIN_ERROR}, status=status.HTTP_401_UNAUTHORIZED)

        User.objects.filter(pk=user.pk).update(failed_logins=0, locked_until=None)

        if user.is_organizer and user.totp_enabled:
            # Password is right; ask for the authenticator code. Not signed in yet.
            request.session.cycle_key()
            request.session["pending_user_id"] = user.id
            request.session["pending_at"] = time.time()
            request.session["mfa_attempts"] = 0
            return Response({"mfa_required": True})

        login(request, user)
        request.session["mfa"] = False
        record(user, "user.login", f"user:{user.id}", ip=_client_ip(request))
        return Response({"user": user_data(user, request.session)})

    @staticmethod
    def _count_failure(user, request):
        User.objects.filter(pk=user.pk).update(failed_logins=F("failed_logins") + 1)
        user.refresh_from_db(fields=["failed_logins"])
        if user.failed_logins >= settings.MAX_FAILED_LOGINS:
            User.objects.filter(pk=user.pk).update(
                failed_logins=0, locked_until=timezone.now() + timedelta(minutes=settings.LOCKOUT_MINUTES))
            alert("Account locked after repeated failed logins", user=user.id, ip=_client_ip(request))
            record(user, "user.locked", f"user:{user.id}", ip=_client_ip(request))


class LoginTwoFactorView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        pending_id = request.session.get("pending_user_id")
        if not pending_id or time.time() - request.session.get("pending_at", 0) > PENDING_MFA_SECONDS:
            request.session.pop("pending_user_id", None)
            return Response({"detail": "Please log in again."}, status=status.HTTP_401_UNAUTHORIZED)

        s = CodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.get(pk=pending_id)
        counter = totp.verify(user.totp_secret, s.validated_data["code"], user.totp_last_counter)
        if counter is None:
            attempts = request.session.get("mfa_attempts", 0) + 1
            request.session["mfa_attempts"] = attempts
            logger.warning("Failed 2FA code", extra={"data": {"user": user.id, "ip": _client_ip(request)}})
            if attempts >= 5:
                request.session.pop("pending_user_id", None)
                alert("Too many failed 2FA codes", user=user.id, ip=_client_ip(request))
                return Response({"detail": "Too many wrong codes. Please log in again."},
                                status=status.HTTP_401_UNAUTHORIZED)
            return Response({"detail": "That code is not correct. Try the newest code in your app."},
                            status=status.HTTP_401_UNAUTHORIZED)

        # Only move forward, so an older code can never be accepted again.
        User.objects.filter(pk=user.pk, totp_last_counter__lt=counter).update(totp_last_counter=counter)
        for key in ("pending_user_id", "pending_at", "mfa_attempts"):
            request.session.pop(key, None)
        login(request, user)
        request.session["mfa"] = True
        record(user, "user.login", f"user:{user.id}", ip=_client_ip(request), mfa=True)
        return Response({"user": user_data(user, request.session)})


class TwoFactorSetupView(APIView):
    """Organizers must set up 2FA before they can manage events."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_organizer or user.totp_enabled:
            return Response({"detail": "Two-step verification is not needed or already set up."},
                            status=status.HTTP_400_BAD_REQUEST)
        secret = request.session.get("pending_totp_secret") or totp.new_secret()
        request.session["pending_totp_secret"] = secret
        return Response({"secret": secret, "uri": totp.provisioning_uri(secret, user.email)})

    def post(self, request):
        user = request.user
        secret = request.session.get("pending_totp_secret")
        if not user.is_organizer or user.totp_enabled or not secret:
            return Response({"detail": "Start the set-up again."}, status=status.HTTP_400_BAD_REQUEST)
        s = CodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        counter = totp.verify(secret, s.validated_data["code"])
        if counter is None:
            return Response({"detail": "That code is not correct. Check the time on your phone and try again."},
                            status=status.HTTP_400_BAD_REQUEST)
        User.objects.filter(pk=user.pk).update(totp_secret=secret, totp_enabled=True, totp_last_counter=counter)
        request.session.pop("pending_totp_secret", None)
        request.session["mfa"] = True
        record(user, "user.2fa_enabled", f"user:{user.id}")
        user.refresh_from_db()
        return Response({"user": user_data(user, request.session)})


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            record(request.user, "user.logout", f"user:{request.user.id}")
        logout(request)  # deletes the session on the server
        return Response(status=status.HTTP_204_NO_CONTENT)
