from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run ledger maintenance tasks: retry dead-letter queue and optional reconciliation"

    def add_arguments(self, parser):
        parser.add_argument("--retry-limit", type=int, default=200)
        parser.add_argument("--reconcile", action="store_true", help="Run reconciliation regardless of feature flag")
        parser.add_argument("--user-id", type=int, help="Optional user scope for reconciliation")
        parser.add_argument("--threshold", type=str, default="0.01", help="Drift threshold for reconcile")

    def handle(self, *args, **options):
        self.stdout.write("Running ledger maintenance...")
        call_command("retry_ledger_shadow_failures", limit=options["retry_limit"])

        should_reconcile = options["reconcile"] or getattr(settings, "LEDGER_RECONCILE_ENABLED", False)
        if should_reconcile:
            reconcile_kwargs = {"threshold": options["threshold"]}
            if options.get("user_id"):
                reconcile_kwargs["user_id"] = options["user_id"]
            call_command("reconcile_ledgers", **reconcile_kwargs)

        self.stdout.write(self.style.SUCCESS("Ledger maintenance complete."))
