from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password, role="buyer"):
        user = self.model(email=self.normalize_email(email).lower(), role=role)
        user.set_password(password)  # Argon2 hash; the password itself is never stored
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        BUYER = "buyer"
        ORGANIZER = "organizer"
        ADMIN = "admin"  # never available at sign-up

    email = models.EmailField(unique=True)
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

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(role__in=["buyer", "organizer", "admin"]),
                                              name="user_role_valid")]

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def __str__(self):
        return self.email
