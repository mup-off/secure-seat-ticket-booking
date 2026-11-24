from django.contrib.auth import password_validation
from rest_framework import serializers

from core.validators import StrictSerializer

from .models import User


class RegisterSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    # Only buyer or organizer can be chosen; admin accounts are never self-service.
    role = serializers.ChoiceField(choices=["buyer", "organizer"])

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with that email already exists. Try logging in.")
        return value

    def validate(self, attrs):
        # Django's validators: minimum 10 characters, not common, not all digits,
        # not too similar to the email.
        password_validation.validate_password(attrs["password"], User(email=attrs["email"]))
        return attrs


class LoginSerializer(StrictSerializer):
    email = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class CodeSerializer(StrictSerializer):
    code = serializers.CharField(max_length=7)


def user_data(user, session):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "totp_enabled": user.totp_enabled,
        "mfa_passed": bool(session.get("mfa")),
    }
