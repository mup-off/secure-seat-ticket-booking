from django.core.management.base import BaseCommand

from orders.services import expire_holds


class Command(BaseCommand):
    help = "Release seats held by checkouts whose 10-minute hold has expired. Run every minute (cron / Task Scheduler)."

    def handle(self, *args, **options):
        n = expire_holds()
        self.stdout.write(f"Released {n} expired hold(s).")
