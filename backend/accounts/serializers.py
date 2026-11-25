from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.validators import StrictSerializer

from .models import User, normalize_username, validate_username


def clean_username(value):
    value = normalize_username(value)
    try:
        validate_username(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages[0])
    return value


class RegisterSerializer(StrictSerializer):
    username = serializers.CharField(max_length=30)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    # Only buyer or organizer can be chosen; admin accounts are never self-service.
    role = serializers.ChoiceField(choices=["buyer", "organizer"])

    def validate_username(self, value):
        value = clean_username(value)
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("That username is taken. Choose another.")
        return value

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with that email already exists. Try logging in.")
        return value

    def validate(self, attrs):
        # Django's validators: minimum 10 characters, not common, not all digits,
        # not too similar to the username or email.
        password_validation.validate_password(attrs["password"], User(username=attrs["username"], email=attrs["email"]))
        return attrs


class LoginSerializer(StrictSerializer):
    username = serializers.CharField(max_length=30)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class CodeSerializer(StrictSerializer):
    code = serializers.CharField(max_length=7)


def user_data(user, session):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "totp_enabled": user.totp_enabled,
        "mfa_passed": bool(session.get("mfa")),
    }
