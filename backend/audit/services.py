import hashlib
import json

from django.db import connection, transaction
from django.utils import timezone

from .models import AuditEntry

GENESIS = "0" * 64
_CHAIN_LOCK_KEY = 7_420_001  # any constant; serialises writers so the chain never forks


def _row_hash(prev_hash, at, actor_id, action, target, details):
    payload = json.dumps([prev_hash, at.isoformat(), actor_id, action, target, details],
                         sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def record(actor, action, target="", **details):
    """Adds one entry to the audit log."""
    actor_id = getattr(actor, "pk", actor)
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", [_CHAIN_LOCK_KEY])
        last = AuditEntry.objects.order_by("-id").values_list("hash", flat=True).first()
        prev = last or GENESIS
        at = timezone.now()
        target = str(target)
        return AuditEntry.objects.create(
            at=at, actor_id=actor_id, action=action, target=target, details=details,
            prev_hash=prev, hash=_row_hash(prev, at, actor_id, action, target, details),
        )


def verify_chain():
    """Returns (True, None) if the chain is intact, else (False, id of first bad row)."""
    prev = GENESIS
    for e in AuditEntry.objects.order_by("id").iterator():
        expected = _row_hash(prev, e.at, e.actor_id, e.action, e.target, e.details)
        if e.prev_hash != prev or e.hash != expected:
            return False, e.id
        prev = e.hash
    return True, None
