from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from expenses.models import (
    Account,
    Expense,
    JournalEntry,
    LedgerPostingFailure,
    LedgerReconciliationReport,
    Loan,
    Notification,
)


class LedgerOpsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ops_user", password="password")
        self.user.profile.currency = "₹"
        self.user.profile.save(update_fields=["currency"])
        self.cash = Account.objects.create(
            user=self.user,
            name="Cash",
            account_type="CASH",
            balance=Decimal("1000.00"),
            currency="₹",
        )
        self.bank = Account.objects.create(
            user=self.user,
            name="Bank",
            account_type="BANK",
            balance=Decimal("3000.00"),
            currency="₹",
        )

    @override_settings(LEDGER_WRITE_ENABLED=True, LEDGER_ENFORCE_BALANCED_WRITE=False)
    def test_shadow_failure_is_dead_lettered(self):
        with patch(
            "expenses.ledger_service.LedgerPostingService.shadow_post_expense_create",
            side_effect=Exception("ledger down"),
        ):
            Expense.objects.create(
                user=self.user,
                date=date.today(),
                amount=Decimal("100.00"),
                description="Coffee",
                category="Food",
                account=self.cash,
                currency="₹",
            )

        failure = LedgerPostingFailure.objects.get()
        self.assertEqual(failure.source_type, "EXPENSE")
        self.assertEqual(failure.status, "PENDING")
        self.assertIn("ledger down", failure.error_message)

    def test_retry_command_resolves_failure(self):
        failure = LedgerPostingFailure.objects.create(
            source_type="EXPENSE",
            source_id=1,
            action="CREATE",
            payload={
                "handler": "expense_create",
                "version_token": "CREATE-1",
                "expense": {
                    "user_id": self.user.id,
                    "amount": "50.00",
                    "currency": "₹",
                    "category": "Food",
                    "description": "Retry expense",
                    "account_id": self.cash.id,
                    "source_id": 1,
                },
            },
            error_message="temporary",
            status="PENDING",
        )

        call_command("retry_ledger_shadow_failures", limit=10)

        failure.refresh_from_db()
        self.assertEqual(failure.status, "RESOLVED")
        self.assertEqual(JournalEntry.objects.filter(source_type="EXPENSE", source_id=1).count(), 1)

    def test_reconcile_command_creates_report(self):
        Expense.objects.create(
            user=self.user,
            date=date.today(),
            amount=Decimal("100.00"),
            description="Coffee",
            category="Food",
            account=self.cash,
            currency="₹",
        )

        call_command("reconcile_ledgers", user_id=self.user.id)

        report = LedgerReconciliationReport.objects.get(user=self.user, account=self.cash)
        self.assertIsNotNone(report)
        self.assertIn(report.status, ["MATCH", "DRIFT"])

    def test_reconcile_command_creates_alert_notification_on_large_drift(self):
        call_command("reconcile_ledgers", user_id=self.user.id, threshold="0.01", alert_threshold="0.01")
        self.assertEqual(Notification.objects.filter(user=self.user, slug__startswith="ledger-drift-").count(), 2)

    def test_retry_income_update_handler(self):
        failure = LedgerPostingFailure.objects.create(
            source_type="INCOME",
            source_id=200,
            action="UPDATE",
            payload={
                "handler": "income_update",
                "version_token": "UPDATE-200",
                "income": {
                    "user_id": self.user.id,
                    "amount": "2000.00",
                    "currency": "₹",
                    "source": "Salary",
                    "description": "Updated income",
                    "account_id": self.bank.id,
                    "source_id": 200,
                },
                "previous_income": {
                    "user_id": self.user.id,
                    "amount": "1800.00",
                    "currency": "₹",
                    "source": "Salary",
                    "description": "Old income",
                    "account_id": self.bank.id,
                    "source_id": 200,
                },
            },
            error_message="temporary",
            status="PENDING",
        )

        call_command("retry_ledger_shadow_failures", limit=10)
        failure.refresh_from_db()
        self.assertEqual(failure.status, "RESOLVED")
        self.assertEqual(JournalEntry.objects.filter(source_type="INCOME", source_id=200).count(), 2)

    def test_retry_transfer_delete_handler(self):
        failure = LedgerPostingFailure.objects.create(
            source_type="TRANSFER",
            source_id=300,
            action="DELETE",
            payload={
                "handler": "transfer_delete",
                "version_token": "DELETE-300",
                "transfer": {
                    "user_id": self.user.id,
                    "amount": "250.00",
                    "description": "Deleted transfer",
                    "from_account_id": self.bank.id,
                    "to_account_id": self.cash.id,
                    "source_id": 300,
                },
            },
            error_message="temporary",
            status="PENDING",
        )

        call_command("retry_ledger_shadow_failures", limit=10)
        failure.refresh_from_db()
        self.assertEqual(failure.status, "RESOLVED")
        self.assertEqual(JournalEntry.objects.filter(source_type="TRANSFER", source_id=300).count(), 1)

    def test_retry_loan_repayment_update_handler(self):
        loan = Loan.objects.create(
            user=self.user,
            name="Home Loan",
            loan_type="HOME",
            initial_principal=Decimal("50000.00"),
            duration_months=120,
            start_date=date.today(),
            currency="₹",
        )

        failure = LedgerPostingFailure.objects.create(
            source_type="LOAN_REPAYMENT",
            source_id=400,
            action="UPDATE",
            payload={
                "handler": "loan_repayment_update",
                "version_token": "UPDATE-400",
                "loan_repayment": {
                    "loan_id": loan.id,
                    "amount": "1500.00",
                    "principal_portion": "1100.00",
                    "interest_portion": "400.00",
                    "from_account_id": self.bank.id,
                    "source_id": 400,
                },
                "previous_loan_repayment": {
                    "loan_id": loan.id,
                    "amount": "1400.00",
                    "principal_portion": "1000.00",
                    "interest_portion": "400.00",
                    "from_account_id": self.bank.id,
                    "source_id": 400,
                },
            },
            error_message="temporary",
            status="PENDING",
        )

        call_command("retry_ledger_shadow_failures", limit=10)
        failure.refresh_from_db()
        self.assertEqual(failure.status, "RESOLVED")
        self.assertEqual(JournalEntry.objects.filter(source_type="LOAN_REPAYMENT", source_id=400).count(), 2)

    def test_run_ledger_maintenance_runs_retry_and_reconcile(self):
        LedgerPostingFailure.objects.create(
            source_type="EXPENSE",
            source_id=900,
            action="CREATE",
            payload={
                "handler": "expense_create",
                "version_token": "CREATE-900",
                "expense": {
                    "user_id": self.user.id,
                    "amount": "60.00",
                    "currency": "₹",
                    "category": "Food",
                    "description": "Maintenance retry",
                    "account_id": self.cash.id,
                    "source_id": 900,
                },
            },
            error_message="temporary",
            status="PENDING",
        )

        call_command("run_ledger_maintenance", retry_limit=10, reconcile=True, user_id=self.user.id, threshold="0.01")

        self.assertTrue(JournalEntry.objects.filter(source_type="EXPENSE", source_id=900).exists())
        self.assertTrue(LedgerReconciliationReport.objects.filter(user=self.user, account=self.cash).exists())
