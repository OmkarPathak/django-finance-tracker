from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from expenses.models import (
    Account,
    JournalLine,
    LedgerReconciliationReport,
    Notification,
)


class Command(BaseCommand):
    help = "Reconcile account balances against ledger-derived balances"

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, help="Reconcile for a single user")
        parser.add_argument("--threshold", type=str, default="0.01", help="Absolute drift threshold")
        parser.add_argument(
            "--alert-threshold",
            type=str,
            default=str(getattr(settings, "LEDGER_RECONCILE_ALERT_THRESHOLD", "10.00")),
            help="Absolute drift amount above which a user alert is created",
        )

    def handle(self, *args, **options):
        threshold = Decimal(options["threshold"])
        alert_threshold = Decimal(options["alert_threshold"])
        accounts = Account.objects.filter(is_active=True).select_related("user")
        if options.get("user_id"):
            accounts = accounts.filter(user_id=options["user_id"])

        as_of_date = timezone.now().date()
        total = 0
        drifts = 0

        for account in accounts:
            total += 1
            debit_total = (
                JournalLine.objects.filter(
                    account_ref=account,
                    direction="DEBIT",
                    journal_entry__status="POSTED",
                )
                .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))
                .get("total", Decimal("0.00"))
            )
            credit_total = (
                JournalLine.objects.filter(
                    account_ref=account,
                    direction="CREDIT",
                    journal_entry__status="POSTED",
                )
                .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))
                .get("total", Decimal("0.00"))
            )

            ledger_balance = (debit_total - credit_total).quantize(Decimal("0.01"))
            account_balance = account.balance.quantize(Decimal("0.01"))
            drift_amount = (account_balance - ledger_balance).quantize(Decimal("0.01"))
            status = "MATCH" if abs(drift_amount) <= threshold else "DRIFT"
            if status == "DRIFT":
                drifts += 1

            if status == "DRIFT" and abs(drift_amount) >= alert_threshold:
                slug = f"ledger-drift-{account.id}-{as_of_date.isoformat()}"
                if not Notification.objects.filter(user=account.user, slug=slug).exists():
                    Notification.objects.create(
                        user=account.user,
                        title="Balance mismatch detected",
                        message=(
                            f"We found a balance mismatch in {account.name}. "
                            f"Drift: {account.currency}{drift_amount}"
                        ),
                        notification_type="SYSTEM",
                        slug=slug,
                        link="/accounts/",
                        metadata={
                            "account_id": account.id,
                            "drift_amount": str(drift_amount),
                            "alert_threshold": str(alert_threshold),
                        },
                    )

            LedgerReconciliationReport.objects.create(
                user=account.user,
                account=account,
                as_of_date=as_of_date,
                account_balance=account_balance,
                ledger_balance=ledger_balance,
                drift_amount=drift_amount,
                status=status,
                metadata={"threshold": str(threshold)},
            )

        self.stdout.write(
            self.style.SUCCESS(f"Reconciliation complete: accounts={total}, drifts={drifts}")
        )
