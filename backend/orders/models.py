import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PAID = "paid"
        EXPIRED = "expired"
        FAILED = "failed"

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    ticket_type = models.ForeignKey("events.TicketType", on_delete=models.PROTECT, related_name="orders")
    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()  # copied from the ticket type at checkout
    total = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    payer_phone = models.CharField(max_length=12)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    payment_ref = models.UUIDField(unique=True)
    idempotency_key = models.UUIDField()
    expires_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # The same checkout submitted twice can only ever create one order.
            models.UniqueConstraint(fields=["buyer", "idempotency_key"], name="order_idempotency"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="order_quantity_positive"),
        ]
        indexes = [models.Index(fields=["status", "expires_at"])]


def new_ticket_token():
    # 256 bits from the operating system's secure random generator (plan, Phase 3).
    return secrets.token_urlsafe(32)


class Ticket(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="tickets")
    token = models.CharField(max_length=64, unique=True, default=new_ticket_token)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                      on_delete=models.PROTECT, related_name="+")


class MockProviderTransaction(models.Model):
    """Stands in for the payment provider's own records, for development and tests.
    With a real provider this table is unused: the status comes from its API."""

    ref = models.UUIDField(primary_key=True)
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    payer = models.CharField(max_length=12)
    status = models.CharField(max_length=16, default="PENDING")
