"""Payment provider adapter.

The app needs only two calls from a mobile money provider (MTN MoMo or Airtel Money):

    request_to_pay(ref, amount, currency, phone)  asks the buyer to approve on their phone
    get_status(ref) -> {"status": "PENDING" | "SUCCESSFUL" | "FAILED", "amount", "currency"}

The buyer types their mobile money PIN on their own phone, in the provider's prompt.
It never reaches this app (plan, Phase 1).

Only the mock provider exists so far. settings.py refuses it in production. A real
MTN MoMo or Airtel adapter has to implement the same two calls, with its API keys
read from environment variables.
"""
from django.conf import settings

from .models import MockProviderTransaction


class MockProvider:
    name = "mock"

    def request_to_pay(self, ref, amount, currency, phone):
        MockProviderTransaction.objects.create(ref=ref, amount=amount, currency=currency, payer=phone)

    def get_status(self, ref):
        tx = MockProviderTransaction.objects.filter(ref=ref).first()
        if not tx:
            return {"status": "NOT_FOUND"}
        return {"status": tx.status, "amount": tx.amount, "currency": tx.currency}

    def simulate_buyer_response(self, ref, approve):
        """Development only: plays the buyer approving or declining on their phone."""
        MockProviderTransaction.objects.filter(ref=ref, status="PENDING").update(
            status="SUCCESSFUL" if approve else "FAILED")


_PROVIDERS = {"mock": MockProvider}


def get_provider():
    try:
        return _PROVIDERS[settings.PAYMENT_PROVIDER]()
    except KeyError:
        raise RuntimeError(f"Unknown PAYMENT_PROVIDER {settings.PAYMENT_PROVIDER!r}")
