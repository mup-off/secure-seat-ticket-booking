from django.conf import settings
from django.db import models


class AuditEntry(models.Model):
    """Append-only, tamper-evident record of important actions (plan, Phase 2: Repudiation).

    - PostgreSQL triggers (see migration 0002) refuse UPDATE and DELETE on this table.
    - Each row stores the SHA-256 hash of the previous row, so a change made by someone
      who bypasses the triggers is detected by audit.services.verify_chain().
    - In production the app's database role should also have UPDATE, DELETE and
      TRUNCATE revoked on this table.
    """

    at = models.DateTimeField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    action = models.CharField(max_length=64)
    target = models.CharField(max_length=64, blank=True, default="")
    details = models.JSONField(default=dict)
    prev_hash = models.CharField(max_length=64)
    hash = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["action", "target"])]

    def __str__(self):
        return f"{self.at:%Y-%m-%d %H:%M} {self.action} {self.target}"
