from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Event(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active"
        CANCELLED = "cancelled"

    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="events")
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=5000)
    venue = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["organizer"]), models.Index(fields=["status", "starts_at"])]


class TicketType(models.Model):
    """A kind of ticket for an event, with a price set by the organizer.

    "sold" counts paid tickets plus tickets held at checkout. The CHECK constraint is
    the last line of defence against overselling: PostgreSQL itself refuses any
    change that would put sold above capacity, whatever the application does.
    """

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="ticket_types")
    name = models.CharField(max_length=60)
    price = models.PositiveIntegerField()  # whole RWF
    capacity = models.PositiveIntegerField()
    sold = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="ticket_type_capacity_positive"),
            models.CheckConstraint(condition=Q(sold__gte=0) & Q(sold__lte=F("capacity")),
                                   name="ticket_type_not_oversold"),
        ]

    @property
    def remaining(self):
        return self.capacity - self.sold
