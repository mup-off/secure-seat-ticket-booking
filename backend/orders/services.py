"""Checkout, payment confirmation, hold expiry and gate check-in.

Security points from the plan that live here:
- The price always comes from the database; the client cannot send one.
- Seats are reserved with a conditional UPDATE inside a transaction, on a row that
  is locked with SELECT ... FOR UPDATE, so two buyers can't both get the last ticket.
  A CHECK constraint in PostgreSQL backs this up (Phase 3: Overselling).
- An idempotency key stops a double-submitted checkout from creating two orders.
- A payment callback is only a hint: status and amount are confirmed with the
  provider, and an order can become "paid" only once (Phase 2).
"""
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from audit.services import record
from core.logging import alert
from events.models import Event, TicketType

from .models import Order, Ticket
from .payment_provider import get_provider

logger = logging.getLogger("secureseat")


class CheckoutError(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.message = message
        self.status = status


def expire_holds():
    """Releases the seats of every pending order whose 10-minute hold has run out."""
    ids = list(Order.objects.filter(status=Order.Status.PENDING, expires_at__lte=timezone.now())
               .values_list("id", flat=True))
    for order_id in ids:
        with transaction.atomic():
            changed = Order.objects.filter(pk=order_id, status=Order.Status.PENDING,
                                           expires_at__lte=timezone.now()).update(status=Order.Status.EXPIRED)
            if changed:
                o = Order.objects.only("ticket_type_id", "quantity").get(pk=order_id)
                TicketType.objects.filter(pk=o.ticket_type_id).update(sold=F("sold") - o.quantity)
    return len(ids)


SALE_STATE_MESSAGES = {
    "stopped": "Sales for this ticket type have been stopped.",
    "not_started": "Sales for this ticket type haven't started yet.",
    "ended": "Sales for this ticket type have ended.",
    "sold_out": "Sorry, this ticket type is sold out.",
}


def create_order(*, buyer, ticket_type_id, quantity, phone, idempotency_key, access_code=""):
    from events.services import end_past_events, hidden_tiers_for_code

    expire_holds()
    end_past_events()
    try:
        with transaction.atomic():
            existing = Order.objects.filter(buyer=buyer, idempotency_key=idempotency_key).first()
            if existing:
                return existing  # same form submitted again: same order

            # Lock this ticket type's row until the transaction ends. A second buyer
            # waits here, then sees the updated "sold" count.
            tt = (TicketType.objects.select_for_update(of=("self",)).select_related("event")
                  .filter(pk=ticket_type_id).first())
            # Drafts and hidden tiers without the right code look exactly like a
            # ticket type that doesn't exist, so they can't be discovered by guessing IDs.
            if not tt or tt.event.status in (Event.Status.DRAFT,):
                raise CheckoutError("That ticket type does not exist.", 404)
            if tt.visibility == TicketType.Visibility.HIDDEN and tt not in hidden_tiers_for_code(tt.event, access_code):
                raise CheckoutError("That ticket type does not exist.", 404)
            if tt.event.status == Event.Status.PAUSED:
                raise CheckoutError("Ticket sales for this event are paused.")
            if tt.event.status != Event.Status.PUBLISHED or tt.event.has_ended():
                raise CheckoutError("Tickets for this event are no longer on sale.")
            state = tt.sale_state()
            if state in SALE_STATE_MESSAGES and state != "sold_out":
                raise CheckoutError(SALE_STATE_MESSAGES[state])
            if quantity > tt.max_per_order:
                raise CheckoutError(f"You can buy at most {tt.max_per_order} of this ticket type per order.", 400)

            reserved = TicketType.objects.filter(
                pk=tt.pk, sold__lte=F("capacity") - quantity
            ).update(sold=F("sold") + quantity)
            if reserved != 1:
                raise CheckoutError("Sorry, there are not enough tickets left.")

            order = Order.objects.create(
                buyer=buyer, ticket_type=tt, quantity=quantity,
                unit_price=tt.price,  # from the database, never from the request
                total=tt.price * quantity, currency=settings.CURRENCY, payer_phone=phone,
                payment_ref=uuid.uuid4(), idempotency_key=idempotency_key,
                expires_at=timezone.now() + timedelta(minutes=settings.HOLD_MINUTES),
            )
    except IntegrityError:
        # Two identical submissions raced; the other one created the order.
        existing = Order.objects.filter(buyer=buyer, idempotency_key=idempotency_key).first()
        if existing:
            return existing
        raise

    record(buyer, "order.created", f"order:{order.id}", total=order.total, quantity=order.quantity)
    try:
        get_provider().request_to_pay(order.payment_ref, order.total, order.currency, order.payer_phone)
    except Exception:
        logger.exception("request_to_pay failed", extra={"data": {"order": order.id}})
        _fail(order.id)
        raise CheckoutError("The payment provider could not be reached. Please try again.", 502)
    return order


def _fail(order_id):
    with transaction.atomic():
        changed = Order.objects.filter(pk=order_id, status=Order.Status.PENDING).update(status=Order.Status.FAILED)
        if changed:
            o = Order.objects.only("ticket_type_id", "quantity").get(pk=order_id)
            TicketType.objects.filter(pk=o.ticket_type_id).update(sold=F("sold") - o.quantity)


def confirm_payment(payment_ref, source):
    """Called by the payment webhook and by the buyer's "check again" button.
    Whatever triggered it, the decision is made only on what the provider reports."""
    order = Order.objects.filter(payment_ref=payment_ref).first()
    if not order:
        return "unknown_order"
    if order.status == Order.Status.PAID:
        return "already_paid"  # replayed callback: no effect

    status = get_provider().get_status(order.payment_ref)
    if status["status"] == "FAILED":
        _fail(order.id)
        record(None, "payment.failed", f"order:{order.id}", source=source)
        return "failed"
    if status["status"] != "SUCCESSFUL":
        return "not_paid"

    if status.get("amount") != order.total or status.get("currency") != order.currency:
        alert("Payment amount does not match order", order=order.id, expected=order.total,
              received=status.get("amount"), currency=status.get("currency"))
        record(None, "payment.amount_mismatch", f"order:{order.id}", expected=order.total,
               received=status.get("amount"), currency=status.get("currency"), source=source)
        return "amount_mismatch"

    with transaction.atomic():
        now = timezone.now()
        # Conditional update: only one caller can move this order from pending to paid.
        changed = Order.objects.filter(pk=order.pk, status=Order.Status.PENDING, expires_at__gt=now).update(
            status=Order.Status.PAID, paid_at=now)
        if changed:
            Ticket.objects.bulk_create([Ticket(order_id=order.pk) for _ in range(order.quantity)])
            outcome = "paid"
        else:
            current = Order.objects.values_list("status", flat=True).get(pk=order.pk)
            outcome = "already_paid" if current == Order.Status.PAID else "paid_after_expiry"

    if outcome == "paid":
        record(None, "payment.confirmed", f"order:{order.id}", amount=order.total, source=source)
    elif outcome == "paid_after_expiry":
        # Money arrived after the seats were released: flag for a manual refund.
        alert("Payment received for an expired order: refund needed", order=order.id)
        record(None, "payment.after_expiry_refund_needed", f"order:{order.id}", amount=order.total, source=source)
    return outcome


def start_refunds_for_event(event):
    """Called when an event is cancelled: releases unpaid holds and refunds every
    paid order. Orders whose refund the provider doesn't accept stay in
    "refund_pending" and are retried by the housekeeping command."""
    with transaction.atomic():
        pending_ids = list(Order.objects.filter(ticket_type__event=event, status=Order.Status.PENDING)
                           .values_list("id", flat=True))
        refund_ids = list(Order.objects.filter(ticket_type__event=event, status=Order.Status.PAID)
                          .values_list("id", flat=True))
        Order.objects.filter(id__in=refund_ids).update(status=Order.Status.REFUND_PENDING)
    for order_id in pending_ids:
        _fail(order_id)
    refunded = retry_refunds(Order.objects.filter(id__in=refund_ids))
    return {"refunds_started": len(refund_ids), "refunded": refunded, "holds_released": len(pending_ids)}


def retry_refunds(queryset=None):
    """Asks the provider to refund each order in refund_pending. Returns how many succeeded."""
    qs = queryset if queryset is not None else Order.objects.all()
    done = 0
    for order in qs.filter(status=Order.Status.REFUND_PENDING):
        try:
            ok = get_provider().refund(order.payment_ref, order.total)
        except Exception:
            logger.exception("refund failed", extra={"data": {"order": order.id}})
            ok = False
        if ok and Order.objects.filter(pk=order.pk, status=Order.Status.REFUND_PENDING).update(
                status=Order.Status.REFUNDED, refunded_at=timezone.now()):
            record(None, "order.refunded", f"order:{order.id}", amount=order.total)
            done += 1
        elif not ok:
            alert("Refund not accepted by the payment provider", order=order.id, amount=order.total)
    return done


def check_in(token, organizer):
    """A ticket is accepted once, and only for the organizer's own events."""
    ticket = (Ticket.objects.select_related("order__ticket_type__event")
              .filter(token=token, order__status=Order.Status.PAID,
                      order__ticket_type__event__organizer=organizer)
              .first())
    if not ticket:
        return {"result": "invalid"}
    info = {"ticket_type": ticket.order.ticket_type.name, "event": ticket.order.ticket_type.event.title}
    changed = Ticket.objects.filter(pk=ticket.pk, checked_in_at__isnull=True).update(
        checked_in_at=timezone.now(), checked_in_by=organizer)
    if not changed:
        ticket.refresh_from_db(fields=["checked_in_at"])
        record(organizer, "ticket.checkin_rejected_reused", f"ticket:{ticket.id}")
        return {"result": "already_used", "checked_in_at": ticket.checked_in_at, **info}
    record(organizer, "ticket.checked_in", f"ticket:{ticket.id}")
    return {"result": "ok", **info}
