import re

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,29}$")
# Names that could be used to pretend to be the site or its staff.
RESERVED_USERNAMES = {
    "admin", "administrator", "root", "support", "help", "secureseat", "staff", "system",
    "organizer", "security", "api", "null", "undefined", "moderator", "official",
}


def normalize_username(value):
    """Usernames are case-insensitive: stored and compared in lowercase, so "Jean"
    and "jean" can't be two different accounts that look alike."""
    return (value or "").strip().lower()


def validate_username(value):
    if not USERNAME_RE.match(value):
        raise ValidationError(
            "Use 3 to 30 characters: letters, numbers, dots, dashes or underscores, starting with a letter or number.")
    if value in RESERVED_USERNAMES:
        raise ValidationError("That username is reserved. Choose another.")


class UserManager(BaseUserManager):
    def create_user(self, username, email, password, role="buyer"):
        user = self.model(username=normalize_username(username), email=self.normalize_email(email).lower(), role=role)
        user.set_password(password)  # Argon2 hash; the password itself is never stored
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username):
        return self.get(username=normalize_username(username))


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        BUYER = "buyer"
        ORGANIZER = "organizer"
        ADMIN = "admin"  # never available at sign-up

    username = models.CharField(max_length=30, unique=True, validators=[validate_username])
    email = models.EmailField(unique=True)  # kept for contact and tickets; not used to log in
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.BUYER)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    # Two-step verification (TOTP), required for organizers.
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    totp_enabled = models.BooleanField(default=False)
    totp_last_counter = models.BigIntegerField(default=0)  # stops a code being used twice

    # Account lockout after repeated failed logins.
    failed_logins = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=["buyer", "organizer", "admin"]), name="user_role_valid"),
            # Belt and braces: the database itself refuses an uppercase username.
            models.CheckConstraint(condition=models.Q(username=Lower("username")),
                                   name="username_lowercase"),
        ]

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def __str__(self):
        return self.username
