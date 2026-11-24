import os
import re

from django.utils import timezone
from rest_framework import serializers

from core.validators import StrictSerializer, normalize_rw_phone

from .models import Event, TicketType
from .services import publish_problems


# ---- Output ----

def cover_url(event):
    if not event.cover_image:
        return None
    version = os.path.splitext(os.path.basename(event.cover_image.name))[0][:12]
    return f"/api/events/{event.id}/cover?v={version}"


def tier_public_data(t, now=None):
    return {
        "id": t.id, "name": t.name, "description": t.description, "price": t.price,
        "remaining": t.remaining, "max_per_order": t.max_per_order,
        "sale_state": t.sale_state(now), "sales_start": t.sales_start, "sales_end": t.sales_end,
        "hidden": t.visibility == TicketType.Visibility.HIDDEN,
    }


def event_public_data(event, unlocked_tiers=()):
    """The event page as buyers see it. Used for the real page AND the organizer's
    preview, so the preview can't drift from what buyers get."""
    now = timezone.now()
    tiers = [t for t in event.ticket_types.all() if t.visibility == TicketType.Visibility.PUBLIC]
    tiers += [t for t in unlocked_tiers if t not in tiers]
    tiers.sort(key=lambda t: (t.position, t.id))
    return {
        "id": event.id, "status": event.status, "title": event.title, "description": event.description,
        "category": event.category, "cover_url": cover_url(event),
        "venue": event.venue, "venue_address": event.venue_address, "online_url": event.online_url,
        "starts_at": event.starts_at, "ends_at": event.ends_at, "contact_phone": event.contact_phone,
        "ticket_types": [tier_public_data(t, now) for t in tiers],
    }


def tier_organizer_data(t):
    return {
        "id": t.id, "name": t.name, "description": t.description, "price": t.price,
        "capacity": t.capacity, "sold": t.sold, "max_per_order": t.max_per_order,
        "sales_start": t.sales_start, "sales_end": t.sales_end, "on_sale": t.on_sale,
        "visibility": t.visibility, "has_access_code": bool(t.access_code_hash), "position": t.position,
        "has_orders": t.sold > 0 or t.orders.exists(),
    }


def event_organizer_data(event):
    return {
        "id": event.id, "status": event.status, "title": event.title, "description": event.description,
        "category": event.category, "cover_url": cover_url(event),
        "venue": event.venue, "venue_address": event.venue_address, "online_url": event.online_url,
        "starts_at": event.starts_at, "ends_at": event.ends_at, "contact_phone": event.contact_phone,
        "updated_at": event.updated_at, "published_at": event.published_at,
        "ticket_types": [tier_organizer_data(t) for t in event.ticket_types.all()],
        "publish_problems": publish_problems(event) if event.status == Event.Status.DRAFT else [],
    }


# ---- Input ----

class EventDetailsSerializer(StrictSerializer):
    """Step 1. Every field is optional so a draft can be saved at any moment; the
    completeness checks run at publish time."""

    title = serializers.CharField(max_length=120, allow_blank=True, required=False)
    description = serializers.CharField(max_length=5000, allow_blank=True, required=False, trim_whitespace=False)
    category = serializers.ChoiceField(choices=Event.Category.choices, allow_blank=True, required=False)
    venue = serializers.CharField(max_length=120, allow_blank=True, required=False)
    venue_address = serializers.CharField(max_length=200, allow_blank=True, required=False)
    online_url = serializers.URLField(max_length=300, allow_blank=True, required=False)
    starts_at = serializers.DateTimeField(allow_null=True, required=False)
    ends_at = serializers.DateTimeField(allow_null=True, required=False)
    contact_phone = serializers.CharField(max_length=20, allow_blank=True, required=False)

    def validate_online_url(self, value):
        if value and not value.lower().startswith("https://"):
            raise serializers.ValidationError("Use a secure link that starts with https://")
        return value

    def validate_contact_phone(self, value):
        return normalize_rw_phone(value) if value else ""


ACCESS_CODE = re.compile(r"^[A-Za-z0-9-]{4,32}$")


class TierSerializer(StrictSerializer):
    name = serializers.CharField(max_length=60)
    description = serializers.CharField(max_length=300, allow_blank=True, required=False)
    price = serializers.IntegerField(min_value=0, max_value=10_000_000)
    capacity = serializers.IntegerField(min_value=1, max_value=100_000)
    max_per_order = serializers.IntegerField(min_value=1, max_value=50, required=False)
    sales_start = serializers.DateTimeField(allow_null=True, required=False)
    sales_end = serializers.DateTimeField(allow_null=True, required=False)
    on_sale = serializers.BooleanField(required=False)
    visibility = serializers.ChoiceField(choices=TicketType.Visibility.choices, required=False)
    access_code = serializers.CharField(max_length=32, required=False, write_only=True)

    def validate_access_code(self, value):
        if not ACCESS_CODE.match(value):
            raise serializers.ValidationError("Use 4 to 32 letters, numbers or dashes.")
        return value


class ReorderSerializer(StrictSerializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100)


class UnlockSerializer(StrictSerializer):
    code = serializers.CharField(max_length=32)
