from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from expenses.ledger_service import LedgerPostingService
from expenses.models import LedgerPostingFailure


class Command(BaseCommand):
    help = "Retry failed ledger shadow postings from dead-letter queue"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Maximum failures to process")

    def handle(self, *args, **options):
        now = timezone.now()
        failures = (
            LedgerPostingFailure.objects
            .filter(status__in=["PENDING", "RETRYING"])
            .filter(Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now))
            .order_by("created_at")[: options["limit"]]
        )
        processed = 0
        resolved = 0
        failed = 0

        for failure in failures:
            processed += 1
            try:
                LedgerPostingService.process_failure(failure)
                resolved += 1
            except Exception:
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed={processed}, Resolved={resolved}, Still failing={failed}"
            )
        )
