import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


def cover_upload_path(instance, filename):
    # Random name: the uploader's filename is never used on disk.
    return f"covers/{uuid.uuid4().hex}.jpg"


class Event(models.Model):
    """An event. It starts as a draft, which may be incomplete; the full checks run
    when the organizer publishes it (events.services.publish_problems).

    Dates are stored in UTC (USE_TZ) and shown in Kigali time.
    """

    class Status(models.TextChoices):
        DRAFT = "draft"
        PUBLISHED = "published"
        PAUSED = "paused"  # sales paused
        ENDED = "ended"
        CANCELLED = "cancelled"

    class Category(models.TextChoices):
        CONCERT = "concert"
        CONFERENCE = "conference"
        SPORTS = "sports"
        CHURCH = "church"
        FESTIVAL = "festival"
        THEATRE = "theatre"
        OTHER = "other"

    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="events")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    # Step 1: details. Blank is allowed while the event is a draft.
    title = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(max_length=5000, blank=True, default="")
    cover_image = models.FileField(upload_to=cover_upload_path, blank=True, default="")
    category = models.CharField(max_length=16, choices=Category.choices, blank=True, default="")
    venue = models.CharField(max_length=120, blank=True, default="")  # venue name
    venue_address = models.CharField(max_length=200, blank=True, default="")
    online_url = models.URLField(max_length=300, blank=True, default="")
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    contact_phone = models.CharField(max_length=12, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organizer"]), models.Index(fields=["status", "starts_at"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(starts_at__isnull=True) | Q(ends_at__isnull=True) | Q(ends_at__gt=F("starts_at")),
                name="event_ends_after_start",
            ),
        ]

    @property
    def is_online(self):
        return bool(self.online_url)

    @property
    def is_editable(self):
        return self.status not in (self.Status.CANCELLED, self.Status.ENDED)

    def has_ended(self):
        return bool(self.ends_at and self.ends_at <= timezone.now())


class TicketType(models.Model):
    """A ticket tier (Regular, VIP, Early bird...).

    "sold" counts paid tickets plus tickets held at checkout. The CHECK constraints
    are the last line of defence: PostgreSQL itself refuses a negative price, a
    quantity below what has been sold, or a sales window that ends before it starts.
    """

    class Visibility(models.TextChoices):
        PUBLIC = "public"
        HIDDEN = "hidden"  # for guests or sponsors, unlocked with a code

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="ticket_types")
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=300, blank=True, default="")
    price = models.PositiveIntegerField()  # whole RWF; 0 = free
    capacity = models.PositiveIntegerField()  # "Quantity" in the UI
    sold = models.PositiveIntegerField(default=0)
    max_per_order = models.PositiveSmallIntegerField(default=10)
    sales_start = models.DateTimeField(null=True, blank=True)  # null: as soon as published
    sales_end = models.DateTimeField(null=True, blank=True)  # null: until the event ends
    on_sale = models.BooleanField(default=True)  # organizer can stop sales for this tier
    visibility = models.CharField(max_length=8, choices=Visibility.choices, default=Visibility.PUBLIC)
    access_code_hash = models.CharField(max_length=128, blank=True, default="")  # hashed, never stored in clear
    position = models.PositiveIntegerField(default=0)  # order buyers see

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="ticket_type_capacity_positive"),
            models.CheckConstraint(condition=Q(sold__gte=0) & Q(sold__lte=F("capacity")),
                                   name="ticket_type_not_oversold"),
            models.CheckConstraint(condition=Q(max_per_order__gte=1) & Q(max_per_order__lte=50),
                                   name="ticket_type_max_per_order_range"),
            models.CheckConstraint(
                condition=Q(sales_start__isnull=True) | Q(sales_end__isnull=True) | Q(sales_end__gt=F("sales_start")),
                name="ticket_type_sales_window_valid",
            ),
        ]

    @property
    def remaining(self):
        return self.capacity - self.sold

    def sale_state(self, now=None):
        """What a buyer sees for this tier right now."""
        now = now or timezone.now()
        if not self.on_sale:
            return "stopped"
        if self.sales_start and self.sales_start > now:
            return "not_started"
        end = self.sales_end or self.event.ends_at
        if end and end <= now:
            return "ended"
        if self.remaining <= 0:
            return "sold_out"
        return "on_sale"
