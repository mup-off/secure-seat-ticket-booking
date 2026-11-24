"""DEVELOPMENT ONLY. Plays the part of the buyer's phone with the mock provider, so the
payment flow can be tried without real MTN/Airtel keys. config/urls.py includes these
routes only outside production, and settings.py refuses the mock provider in
production too."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .payment_provider import get_provider
from .serializers import DevPaySerializer
from .views import own_order


class DevPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = own_order(request, order_id)
        s = DevPaySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        get_provider().simulate_buyer_response(order.payment_ref, s.validated_data["decision"] == "approve")
        # A real provider would now call the webhook; do the same.
        services.confirm_payment(order.payment_ref, "mock_callback")
        return Response({"id": order.id})
