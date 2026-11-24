from django.utils import timezone
from rest_framework import serializers

from core.validators import StrictSerializer

from .models import Event, TicketType


class TicketTypePublicSerializer(serializers.ModelSerializer):
    remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = TicketType
        fields = ["id", "name", "price", "remaining"]


class TicketTypeOrganizerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ["id", "name", "price", "capacity", "sold"]


class EventListSerializer(serializers.ModelSerializer):
    from_price = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Event
        fields = ["id", "title", "venue", "starts_at", "from_price"]


class EventDetailSerializer(serializers.ModelSerializer):
    ticket_types = TicketTypePublicSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = ["id", "title", "description", "venue", "starts_at", "ticket_types"]


class OrganizerEventSerializer(serializers.ModelSerializer):
    ticket_types = TicketTypeOrganizerSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = ["id", "title", "description", "venue", "starts_at", "status", "ticket_types"]


class EventCreateSerializer(StrictSerializer):
    title = serializers.CharField(max_length=120)
    venue = serializers.CharField(max_length=120)
    description = serializers.CharField(max_length=5000)
    starts_at = serializers.DateTimeField()

    def validate_starts_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("The start date must be in the future.")
        return value


class TicketTypeCreateSerializer(StrictSerializer):
    name = serializers.CharField(max_length=60)
    price = serializers.IntegerField(min_value=0, max_value=10_000_000)
    capacity = serializers.IntegerField(min_value=1, max_value=100_000)
