import logging
import re

from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsBuyer, IsOrganizerWith2FA
from audit.services import record
from core.logging import alert

from . import services
from .models import Order
from .serializers import CheckInSerializer, CheckoutSerializer, order_data

logger = logging.getLogger("secureseat")
UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")
PRICE_LIKE = {"price", "unit_price", "total", "amount", "unitPrice"}


class CheckoutView(APIView):
    permission_classes = [IsBuyer]
    throttle_classes = [ScopedRateThrottle]  # per user
    throttle_scope = "checkout"

    def post(self, request):
        s = CheckoutSerializer(data=request.data)
        try:
            s.is_valid(raise_exception=True)
        except ValidationError as exc:
            unexpected = exc.detail.get("unexpected_fields") if isinstance(exc.detail, dict) else None
            if unexpected:
                fields = [str(f) for f in unexpected]
                if PRICE_LIKE & set(fields):
                    alert("Checkout rejected: client sent a price (possible tampering)",
                          user=request.user.id, fields=fields, ip=request.META.get("REMOTE_ADDR"))
                record(request.user, "checkout.rejected_tampering", "", fields=fields)
            raise
        try:
            order = services.create_order(buyer=request.user, **s.validated_data)
        except services.CheckoutError as exc:
            return Response({"detail": exc.message}, status=exc.status)
        return Response({"id": order.id}, status=status.HTTP_201_CREATED)


def own_order(request, order_id):
    """Only the buyer who placed an order can see it. Everyone else gets 404, so an
    attacker can't even tell which order IDs exist (plan, Phase 4)."""
    order = (Order.objects.select_related("ticket_type__event")
             .filter(pk=order_id, buyer=request.user).first())
    if not order:
        raise Http404
    return order


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (Order.objects.filter(buyer=request.user).select_related("ticket_type__event")
                  .order_by("-created_at")[:100])
        return Response([order_data(o) for o in orders])


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        services.expire_holds()
        order = own_order(request, order_id)
        tickets = list(order.tickets.order_by("id")) if order.status == Order.Status.PAID else []
        data = order_data(order, tickets)
        data["dev_payments"] = not settings.IS_PRODUCTION
        return Response(data)


class OrderRefreshView(APIView):
    """'I have approved it on my phone': asks the provider for the real status."""

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = own_order(request, order_id)
        services.confirm_payment(order.payment_ref, "buyer_refresh")
        return Response({"id": order.id})


class PaymentWebhookView(APIView):
    """Payment provider callback (plan, Phase 2).

    The body is treated only as a hint that something changed. It carries no trust:
    confirm_payment() asks the provider for the real status and amount, and moves
    the order to "paid" at most once, so fake callbacks and replays have no effect.
    No session or CSRF here: the provider is not a browser.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "webhook"

    def post(self, request):
        ref = request.data.get("referenceId") or request.data.get("externalId") if isinstance(request.data, dict) else None
        if not isinstance(ref, str) or not UUID_RE.match(ref):
            return Response({"detail": "invalid reference"}, status=status.HTTP_400_BAD_REQUEST)
        result = services.confirm_payment(ref, "webhook")
        logger.info("Payment webhook processed", extra={"data": {"result": result, "ip": request.META.get("REMOTE_ADDR")}})
        # Same reply whatever happened, so the endpoint can't be used to probe orders.
        return Response({"received": True})


class CheckInView(APIView):
    permission_classes = [IsOrganizerWith2FA]

    def post(self, request):
        s = CheckInSerializer(data=request.data)
        if not s.is_valid():
            return Response({"result": "invalid"}, status=status.HTTP_409_CONFLICT)
        outcome = services.check_in(s.validated_data["token"], request.user)
        return Response(outcome, status=status.HTTP_200_OK if outcome["result"] == "ok" else status.HTTP_409_CONFLICT)
