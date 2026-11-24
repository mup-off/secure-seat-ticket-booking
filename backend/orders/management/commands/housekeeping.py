from django.core.management.base import BaseCommand

from events.services import end_past_events
from orders.services import expire_holds, retry_refunds


class Command(BaseCommand):
    help = ("Release expired checkout holds, mark finished events as ended, and retry refunds "
            "the provider hasn't accepted yet. Schedule it every minute (cron / Task Scheduler).")

    def handle(self, *args, **options):
        holds = expire_holds()
        ended = end_past_events()
        refunds = retry_refunds()
        self.stdout.write(f"Released {holds} hold(s), ended {ended} event(s), completed {refunds} refund(s).")
