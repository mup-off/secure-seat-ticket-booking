"""Public event pages and organizer event management.

Least privilege (plan, Phase 2): every organizer query is filtered by
organizer=request.user, so one organizer can never see or change another's events.
Records that don't exist and records that aren't yours both give 404, so IDs
can't be probed.
"""
from django.db.models import Count, Min, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOrganizerWith2FA
from audit.services import record
from orders.models import Order

from .models import Event, TicketType
from .serializers import (EventCreateSerializer, EventDetailSerializer, EventListSerializer,
                          OrganizerEventSerializer, TicketTypeCreateSerializer)


def _on_sale():
    return Event.objects.filter(status=Event.Status.ACTIVE, starts_at__gt=timezone.now())


class EventListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        events = _on_sale().annotate(from_price=Min("ticket_types__price")).order_by("starts_at")[:100]
        return Response(EventListSerializer(events, many=True).data)


class EventDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, event_id):
        event = get_object_or_404(_on_sale().prefetch_related("ticket_types"), pk=event_id)
        return Response(EventDetailSerializer(event).data)


def own_event(request, event_id):
    return get_object_or_404(Event, pk=event_id, organizer=request.user)


class OrganizerEventsView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def get(self, request):
        events = (Event.objects.filter(organizer=request.user)
                  .annotate(sold=Sum("ticket_types__sold"), capacity=Sum("ticket_types__capacity"))
                  .order_by("-starts_at"))
        return Response([
            {"id": e.id, "title": e.title, "starts_at": e.starts_at, "status": e.status,
             "sold": e.sold or 0, "capacity": e.capacity or 0}
            for e in events
        ])

    def post(self, request):
        s = EventCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        event = Event.objects.create(organizer=request.user, **s.validated_data)
        record(request.user, "event.created", f"event:{event.id}", title=event.title)
        return Response(OrganizerEventSerializer(event).data, status=status.HTTP_201_CREATED)


class OrganizerEventDetailView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def get(self, request, event_id):
        return Response(OrganizerEventSerializer(own_event(request, event_id)).data)


class TicketTypeCreateView(APIView):
    """Only the organizer sets prices. There is deliberately no endpoint to change a
    price later, so a buyer always pays the price shown when they checked out."""

    permission_classes = [IsOrganizerWith2FA]

    def post(self, request, event_id):
        event = own_event(request, event_id)
        if event.status != Event.Status.ACTIVE:
            return Response({"detail": "This event is cancelled."}, status=status.HTTP_409_CONFLICT)
        s = TicketTypeCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        tt = TicketType.objects.create(event=event, **s.validated_data)
        record(request.user, "ticket_type.created", f"ticket_type:{tt.id}",
               event=event.id, price=tt.price, capacity=tt.capacity)
        return Response(OrganizerEventSerializer(event).data, status=status.HTTP_201_CREATED)


class EventCancelView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def post(self, request, event_id):
        event = own_event(request, event_id)
        Event.objects.filter(pk=event.pk, organizer=request.user).update(status=Event.Status.CANCELLED)
        # Answers "I never cancelled that event" (plan, Phase 2: Repudiation).
        record(request.user, "event.cancelled", f"event:{event.id}", ip=request.META.get("REMOTE_ADDR"))
        event.refresh_from_db()
        return Response(OrganizerEventSerializer(event).data)


class AttendeeListView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def get(self, request, event_id):
        event = own_event(request, event_id)
        orders = (Order.objects.filter(ticket_type__event=event, status=Order.Status.PAID)
                  .select_related("buyer", "ticket_type")
                  .annotate(checked_in=Count("tickets", filter=Q(tickets__checked_in_at__isnull=False)))
                  .order_by("paid_at"))
        # Viewing personal data is itself recorded (Law No. 058/2021).
        record(request.user, "event.attendees_viewed", f"event:{event.id}")
        return Response({
            "event": {"id": event.id, "title": event.title},
            "attendees": [
                {"email": o.buyer.email, "ticket_type": o.ticket_type.name, "quantity": o.quantity,
                 "checked_in": o.checked_in, "paid_at": o.paid_at}
                for o in orders
            ],
        })
