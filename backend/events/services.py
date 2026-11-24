"""Event lifecycle and ticket tier rules, enforced on the server.

Statuses:  draft -> published <-> paused -> ended
           draft / published / paused -> cancelled (starts refunds)
"""
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from audit.services import record

from .models import Event, TicketType

S = Event.Status


class RuleError(Exception):
    """A business rule was broken. `status` is the HTTP status to answer with."""

    def __init__(self, message, status=400, problems=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.problems = problems or []


def end_past_events():
    """Marks published or paused events whose end time has passed as ended."""
    return Event.objects.filter(status__in=[S.PUBLISHED, S.PAUSED], ends_at__lte=timezone.now()).update(
        status=S.ENDED)


def publish_problems(event):
    """Everything that must be true before an event can be published.
    Returns a list of plain-language problems; empty means ready."""
    problems = []
    if not event.title.strip():
        problems.append("Add a title.")
    if not event.description.strip():
        problems.append("Add a description.")
    if not event.category:
        problems.append("Choose a category.")
    if not event.online_url and not (event.venue.strip() and event.venue_address.strip()):
        problems.append("Add the venue name and address, or an online link.")
    if not event.contact_phone:
        problems.append("Add a contact phone number.")
    if not event.starts_at or not event.ends_at:
        problems.append("Set the start and end date and time.")
    else:
        if event.starts_at <= timezone.now():
            problems.append("The start time must be in the future.")
        if event.ends_at <= event.starts_at:
            problems.append("The event must end after it starts.")
    tiers = list(event.ticket_types.all())
    if not tiers:
        problems.append("Add at least one ticket type.")
    for t in tiers:
        problems.extend(tier_problems(t, event))
    return problems


def tier_problems(tier, event):
    problems = []
    if tier.price < 0 or tier.capacity < 1:
        problems.append(f"{tier.name}: price can't be negative and quantity must be at least 1.")
    if event.ends_at and tier.sales_end and tier.sales_end > event.ends_at:
        problems.append(f"{tier.name}: sales must end before the event ends.")
    if tier.sales_start and tier.sales_end and tier.sales_end <= tier.sales_start:
        problems.append(f"{tier.name}: sales must end after they start.")
    if event.ends_at and tier.sales_start and tier.sales_start >= event.ends_at:
        problems.append(f"{tier.name}: sales must start before the event ends.")
    if tier.visibility == TicketType.Visibility.HIDDEN and not tier.access_code_hash:
        problems.append(f"{tier.name}: a hidden ticket type needs an access code.")
    return problems


def _locked(event):
    return Event.objects.select_for_update().get(pk=event.pk)


def publish(event, user):
    with transaction.atomic():
        event = _locked(event)
        if event.status != S.DRAFT:
            raise RuleError("Only a draft can be published.", 409)
        problems = publish_problems(event)
        if problems:
            raise RuleError("This event is not ready to publish.", 400, problems)
        event.status = S.PUBLISHED
        event.published_at = timezone.now()
        event.save(update_fields=["status", "published_at", "updated_at"])
    record(user, "event.published", f"event:{event.id}")
    return event


def pause(event, user):
    with transaction.atomic():
        event = _locked(event)
        if event.status != S.PUBLISHED:
            raise RuleError("Only a published event can have its sales paused.", 409)
        event.status = S.PAUSED
        event.save(update_fields=["status", "updated_at"])
    record(user, "event.sales_paused", f"event:{event.id}")
    return event


def resume(event, user):
    with transaction.atomic():
        event = _locked(event)
        if event.status != S.PAUSED:
            raise RuleError("Sales are not paused.", 409)
        if event.has_ended():
            raise RuleError("This event has already ended.", 409)
        event.status = S.PUBLISHED
        event.save(update_fields=["status", "updated_at"])
    record(user, "event.sales_resumed", f"event:{event.id}")
    return event


def cancel(event, user):
    """Cancels the event and starts refunds for everyone who paid."""
    from orders.services import start_refunds_for_event  # avoids a circular import

    with transaction.atomic():
        event = _locked(event)
        if event.status not in (S.DRAFT, S.PUBLISHED, S.PAUSED):
            raise RuleError("This event can't be cancelled.", 409)
        event.status = S.CANCELLED
        event.save(update_fields=["status", "updated_at"])
    record(user, "event.cancelled", f"event:{event.id}")
    summary = start_refunds_for_event(event)
    return event, summary


# ---- Ticket tiers ----

def _require_editable(event):
    if not event.is_editable:
        raise RuleError("This event can no longer be changed.", 409)


def add_tier(event, user, data, access_code=None):
    _require_editable(event)
    with transaction.atomic():
        event = _locked(event)
        position = (event.ticket_types.aggregate(m=Max("position"))["m"] or 0) + 1
        tier = TicketType(event=event, position=position, **data)
        if access_code:
            tier.access_code_hash = _hash_code(access_code)
        problems = tier_problems(tier, event)
        if problems:
            raise RuleError(problems[0])
        tier.save()
    record(user, "ticket_type.created", f"ticket_type:{tier.id}", event=event.id, price=tier.price,
           capacity=tier.capacity, visibility=tier.visibility)
    return tier


def update_tier(tier, user, data, access_code=None):
    """Price changes apply only to new orders: each order keeps the price it was
    charged (Order.unit_price). Quantity can't go below what has been sold."""
    _require_editable(tier.event)
    with transaction.atomic():
        # Lock the row so a checkout can't sell a ticket between our check and our save.
        tier = TicketType.objects.select_for_update().select_related("event").get(pk=tier.pk)
        old = {"price": tier.price, "capacity": tier.capacity, "on_sale": tier.on_sale}
        for field, value in data.items():
            setattr(tier, field, value)
        if tier.capacity < tier.sold:
            raise RuleError(f"Quantity can't be lower than the {tier.sold} tickets already sold or held.")
        if access_code:
            tier.access_code_hash = _hash_code(access_code)
        if tier.visibility == TicketType.Visibility.PUBLIC:
            tier.access_code_hash = ""
        problems = tier_problems(tier, tier.event)
        if problems:
            raise RuleError(problems[0])
        tier.save()
    changes = {k: [v, getattr(tier, k)] for k, v in old.items() if getattr(tier, k) != v}
    record(user, "ticket_type.updated", f"ticket_type:{tier.id}", **changes)
    return tier


def delete_tier(tier, user):
    _require_editable(tier.event)
    with transaction.atomic():
        tier = TicketType.objects.select_for_update().get(pk=tier.pk)
        if tier.sold > 0 or tier.orders.exists():
            raise RuleError("Tickets of this type have been ordered, so it can't be deleted. "
                            "You can stop its sales instead.", 409)
        tier_id = tier.id
        tier.delete()
    record(user, "ticket_type.deleted", f"ticket_type:{tier_id}")


def reorder_tiers(event, user, ids):
    _require_editable(event)
    with transaction.atomic():
        event = _locked(event)
        current = list(event.ticket_types.values_list("id", flat=True))
        if sorted(ids) != sorted(current) or len(set(ids)) != len(ids):
            raise RuleError("The list must contain each ticket type of this event exactly once.")
        for position, tier_id in enumerate(ids, start=1):
            TicketType.objects.filter(pk=tier_id, event=event).update(position=position)
    record(user, "ticket_type.reordered", f"event:{event.id}", order=ids)


def check_event_dates(event, new_ends_at):
    """Moving the event end must not leave a tier selling after the event ends."""
    if new_ends_at is None:
        return
    late = event.ticket_types.filter(sales_end__gt=new_ends_at).values_list("name", flat=True)
    if late:
        raise RuleError(f"Ticket sales for {', '.join(late)} end after this time. Change those first.")


# ---- Hidden tiers ----

def _hash_code(code):
    from django.contrib.auth.hashers import make_password

    return make_password(code.strip().upper())


def hidden_tiers_for_code(event, code):
    """Returns the hidden tiers that this access code unlocks (usually one)."""
    code = (code or "").strip().upper()
    if not code:
        return []
    return [t for t in event.ticket_types.filter(visibility=TicketType.Visibility.HIDDEN)
            if t.access_code_hash and check_password(code, t.access_code_hash)]
