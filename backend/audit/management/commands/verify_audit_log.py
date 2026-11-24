from django.core.management.base import BaseCommand, CommandError

from audit.services import verify_chain


class Command(BaseCommand):
    help = "Check that the audit log's hash chain is intact (detects edited or deleted rows)."

    def handle(self, *args, **options):
        ok, bad_id = verify_chain()
        if not ok:
            raise CommandError(f"Audit log tampering detected at entry {bad_id}")
        self.stdout.write(self.style.SUCCESS("Audit log chain is intact."))
