from django.conf import settings
from rest_framework import serializers

from core.validators import StrictSerializer, normalize_rw_phone


class CheckoutSerializer(StrictSerializer):
    """The client is not allowed to set or change the price. This serializer accepts
    only these four fields; a request with "price", "total", "amount" or any other
    field is rejected as a whole (StrictSerializer)."""

    ticket_type_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=settings.MAX_TICKETS_PER_ORDER)
    phone = serializers.CharField(max_length=20)
    idempotency_key = serializers.UUIDField()
    access_code = serializers.CharField(max_length=32, required=False, allow_blank=True)  # for hidden tiers

    def validate_phone(self, value):
        return normalize_rw_phone(value)


class CheckInSerializer(StrictSerializer):
    token = serializers.RegexField(r"^[A-Za-z0-9_-]{43}$", max_length=43)


class DevPaySerializer(StrictSerializer):
    decision = serializers.ChoiceField(choices=["approve", "decline"])


def order_data(order, tickets=None):
    tt = order.ticket_type
    data = {
        "id": order.id,
        "status": order.status,
        "event": {"id": tt.event.id, "title": tt.event.title, "venue": tt.event.venue,
                  "starts_at": tt.event.starts_at},
        "ticket_type": tt.name,
        "quantity": order.quantity,
        "unit_price": order.unit_price,
        "total": order.total,
        "currency": order.currency,
        "expires_at": order.expires_at,
        "paid_at": order.paid_at,
        "created_at": order.created_at,
    }
    if tickets is not None:
        data["tickets"] = [{"id": t.id, "token": t.token, "checked_in_at": t.checked_in_at} for t in tickets]
    return data
