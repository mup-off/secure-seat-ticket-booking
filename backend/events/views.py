"""Public event pages and organizer event management.

Least privilege (plan, Phase 2): every organizer query is filtered by
organizer=request.user, so one organizer can never see or change another's events.
Records that don't exist and records that aren't yours both give 404.
"""
from django.db.models import Count, Min, Q, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsOrganizerWith2FA
from audit.services import record
from orders.models import Order

from . import services
from .images import ImageRejected, clean_cover
from .models import Event, TicketType
from .serializers import (EventDetailsSerializer, ReorderSerializer, TierSerializer, UnlockSerializer, cover_url,
                          event_organizer_data, event_public_data, tier_public_data)

S = Event.Status
PUBLIC_STATUSES = [S.PUBLISHED, S.PAUSED, S.ENDED, S.CANCELLED]


def rule_error_response(exc):
    body = {"detail": exc.message}
    if exc.problems:
        body["problems"] = exc.problems
    return Response(body, status=exc.status)


# ---------- Public ----------

class EventListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        services.end_past_events()
        events = (Event.objects.filter(status__in=[S.PUBLISHED, S.PAUSED])
                  .annotate(from_price=Min("ticket_types__price",
                                           filter=Q(ticket_types__visibility=TicketType.Visibility.PUBLIC)))
                  .order_by("starts_at")[:100])
        return Response([
            {"id": e.id, "title": e.title, "category": e.category, "venue": e.venue, "online": bool(e.online_url),
             "starts_at": e.starts_at, "status": e.status, "from_price": e.from_price, "cover_url": cover_url(e)}
            for e in events
        ])


def public_event(event_id):
    services.end_past_events()
    return get_object_or_404(Event.objects.prefetch_related("ticket_types"), pk=event_id,
                             status__in=PUBLIC_STATUSES)


class EventDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, event_id):
        return Response(event_public_data(public_event(event_id)))


class EventUnlockView(APIView):
    """Reveals hidden ticket types (for guests or sponsors) to someone with the code.
    Rate-limited per IP so codes can't be guessed."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "unlock"

    def post(self, request, event_id):
        event = public_event(event_id)
        s = UnlockSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        tiers = services.hidden_tiers_for_code(event, s.validated_data["code"])
        if not tiers:
            return Response({"detail": "That code doesn't unlock any tickets for this event."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({"ticket_types": [tier_public_data(t) for t in tiers]})


class EventCoverView(APIView):
    """Sends a cover image. Draft covers are visible only to their organizer."""

    permission_classes = [AllowAny]

    def get(self, request, event_id):
        event = Event.objects.filter(pk=event_id).first()
        if not event or not event.cover_image:
            raise Http404
        if event.status == S.DRAFT and not (request.user.is_authenticated and event.organizer_id == request.user.id):
            raise Http404
        response = FileResponse(event.cover_image.open("rb"), content_type="image/jpeg")
        response["Cache-Control"] = "private, max-age=3600"
        return response


# ---------- Organizer ----------

def own_event(request, event_id):
    return get_object_or_404(Event.objects.prefetch_related("ticket_types"), pk=event_id, organizer=request.user)


def own_tier(request, event_id, tier_id):
    return get_object_or_404(TicketType.objects.select_related("event"), pk=tier_id, event_id=event_id,
                             event__organizer=request.user)


class OrganizerEventsView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def get(self, request):
        services.end_past_events()
        events = (Event.objects.filter(organizer=request.user)
                  .annotate(sold=Sum("ticket_types__sold"), capacity=Sum("ticket_types__capacity"))
                  .order_by("-updated_at"))
        return Response([
            {"id": e.id, "title": e.title, "starts_at": e.starts_at, "status": e.status,
             "sold": e.sold or 0, "capacity": e.capacity or 0, "updated_at": e.updated_at}
            for e in events
        ])

    def post(self, request):
        """Starts a new draft. Details can be sent now or saved later, bit by bit."""
        s = EventDetailsSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        if data.get("starts_at") and data.get("ends_at") and data["ends_at"] <= data["starts_at"]:
            return Response({"detail": "The event must end after it starts."}, status=400)
        event = Event.objects.create(organizer=request.user, **data)
        record(request.user, "event.draft_created", f"event:{event.id}")
        return Response(event_organizer_data(event), status=status.HTTP_201_CREATED)


class OrganizerEventDetailView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def get(self, request, event_id):
        return Response(event_organizer_data(own_event(request, event_id)))

    def patch(self, request, event_id):
        """Saves step-1 details. Called often by the wizard's autosave."""
        event = own_event(request, event_id)
        if not event.is_editable:
            return Response({"detail": "This event can no longer be changed."}, status=409)
        s = EventDetailsSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        starts = data.get("starts_at", event.starts_at)
        ends = data.get("ends_at", event.ends_at)
        if starts and ends and ends <= starts:
            return Response({"detail": "The event must end after it starts."}, status=400)
        if event.status != S.DRAFT:
            # A live event must stay complete: these can't be cleared after publishing.
            for field in ("title", "description", "category", "contact_phone", "starts_at", "ends_at"):
                if field in data and not data[field]:
                    return Response({"detail": f"{field.replace('_', ' ').capitalize()} can't be empty once published."},
                                    status=400)
        try:
            services.check_event_dates(event, ends)
        except services.RuleError as exc:
            return rule_error_response(exc)
        for field, value in data.items():
            setattr(event, field, value)
        event.save()
        if event.status != S.DRAFT:
            record(request.user, "event.updated", f"event:{event.id}", fields=sorted(data))
        return Response(event_organizer_data(own_event(request, event_id)))

    def delete(self, request, event_id):
        """Only drafts can be deleted. Published events are cancelled instead."""
        event = own_event(request, event_id)
        if event.status != S.DRAFT:
            return Response({"detail": "Only drafts can be deleted. Cancel the event instead."}, status=409)
        if Order.objects.filter(ticket_type__event=event).exists():
            return Response({"detail": "This event has orders and can't be deleted."}, status=409)
        event.ticket_types.all().delete()
        if event.cover_image:
            event.cover_image.delete(save=False)
        event.delete()
        record(request.user, "event.draft_deleted", f"event:{event_id}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventCoverUploadView(APIView):
    permission_classes = [IsOrganizerWith2FA]
    parser_classes = [MultiPartParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "upload"

    def post(self, request, event_id):
        event = own_event(request, event_id)
        if not event.is_editable:
            return Response({"detail": "This event can no longer be changed."}, status=409)
        upload = request.FILES.get("image")
        if not upload or set(request.FILES) != {"image"}:
            return Response({"detail": "Send one image in the 'image' field."}, status=400)
        try:
            clean = clean_cover(upload)
        except ImageRejected as exc:
            return Response({"detail": str(exc)}, status=400)
        old = event.cover_image.name if event.cover_image else None
        event.cover_image.save("cover.jpg", clean, save=True)
        if old:
            event.cover_image.storage.delete(old)
        record(request.user, "event.cover_uploaded", f"event:{event.id}")
        return Response({"cover_url": cover_url(event)})

    def delete(self, request, event_id):
        event = own_event(request, event_id)
        if event.cover_image:
            event.cover_image.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TierListView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def post(self, request, event_id):
        event = own_event(request, event_id)
        s = TierSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        code = data.pop("access_code", None)
        try:
            services.add_tier(event, request.user, data, access_code=code)
        except services.RuleError as exc:
            return rule_error_response(exc)
        return Response(event_organizer_data(own_event(request, event_id)), status=status.HTTP_201_CREATED)


class TierDetailView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def patch(self, request, event_id, tier_id):
        tier = own_tier(request, event_id, tier_id)
        s = TierSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        code = data.pop("access_code", None)
        try:
            services.update_tier(tier, request.user, data, access_code=code)
        except services.RuleError as exc:
            return rule_error_response(exc)
        return Response(event_organizer_data(own_event(request, event_id)))

    def delete(self, request, event_id, tier_id):
        tier = own_tier(request, event_id, tier_id)
        try:
            services.delete_tier(tier, request.user)
        except services.RuleError as exc:
            return rule_error_response(exc)
        return Response(event_organizer_data(own_event(request, event_id)))


class TierReorderView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def post(self, request, event_id):
        event = own_event(request, event_id)
        s = ReorderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            services.reorder_tiers(event, request.user, s.validated_data["ids"])
        except services.RuleError as exc:
            return rule_error_response(exc)
        return Response(event_organizer_data(own_event(request, event_id)))


class EventStatusView(APIView):
    """POST /publish, /pause, /resume, /cancel."""

    permission_classes = [IsOrganizerWith2FA]
    transition = None

    def post(self, request, event_id):
        event = own_event(request, event_id)
        try:
            if self.transition == "cancel":
                event, summary = services.cancel(event, request.user)
                data = event_organizer_data(own_event(request, event_id))
                data["refunds"] = summary
                return Response(data)
            getattr(services, self.transition)(event, request.user)
        except services.RuleError as exc:
            return rule_error_response(exc)
        return Response(event_organizer_data(own_event(request, event_id)))


class EventPreviewView(APIView):
    """Step 3: the event page exactly as buyers will see it (same function as the real page)."""

    permission_classes = [IsOrganizerWith2FA]

    def get(self, request, event_id):
        event = own_event(request, event_id)
        hidden = list(event.ticket_types.filter(visibility=TicketType.Visibility.HIDDEN))
        return Response({"page": event_public_data(event), "hidden_tiers": [t.name for t in hidden]})


class AttendeeListView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def get(self, request, event_id):
        event = own_event(request, event_id)
        orders = (Order.objects.filter(ticket_type__event=event,
                                       status__in=[Order.Status.PAID, Order.Status.REFUND_PENDING, Order.Status.REFUNDED])
                  .select_related("buyer", "ticket_type")
                  .annotate(checked_in=Count("tickets", filter=Q(tickets__checked_in_at__isnull=False)))
                  .order_by("paid_at"))
        # Viewing personal data is itself recorded (Law No. 058/2021).
        record(request.user, "event.attendees_viewed", f"event:{event.id}")
        return Response({
            "event": {"id": event.id, "title": event.title},
            "attendees": [
                {"username": o.buyer.username, "email": o.buyer.email, "ticket_type": o.ticket_type.name, "quantity": o.quantity,
                 "unit_price": o.unit_price, "status": o.status, "checked_in": o.checked_in, "paid_at": o.paid_at}
                for o in orders
            ],
        })
