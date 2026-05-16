from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from expenses.ledger_read_service import LedgerReadService
from expenses.models import Account, Expense


class LedgerReadServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reader", password="pass")
        self.user.profile.currency = "₹"
        self.user.profile.save(update_fields=["currency"])

        self.cash = Account.objects.create(
            user=self.user,
            name="Cash",
            account_type="CASH",
            balance=Decimal("1000.00"),
            currency="₹",
        )

    @override_settings(LEDGER_READ_ENABLED=False, LEDGER_WRITE_ENABLED=True)
    def test_account_balance_falls_back_to_account_model_when_read_flag_off(self):
        Expense.objects.create(
            user=self.user,
            date=date.today(),
            amount=Decimal("100.00"),
            description="Lunch",
            category="Food",
            account=self.cash,
            currency="₹",
        )
        self.cash.refresh_from_db()
        self.assertEqual(LedgerReadService.get_account_balance(self.cash), self.cash.balance)

    @override_settings(LEDGER_READ_ENABLED=True, LEDGER_WRITE_ENABLED=True)
    def test_account_balance_reads_from_ledger_when_enabled(self):
        Expense.objects.create(
            user=self.user,
            date=date.today(),
            amount=Decimal("100.00"),
            description="Lunch",
            category="Food",
            account=self.cash,
            currency="₹",
        )
        self.cash.refresh_from_db()
        # Without an opening balance adjustment journal, read adapter safely falls back.
        self.assertEqual(LedgerReadService.get_account_balance(self.cash), Decimal("900.00"))
        self.assertEqual(LedgerReadService.get_account_ledger_delta(self.cash), Decimal("-100.00"))

    @override_settings(LEDGER_READ_ENABLED=True, LEDGER_WRITE_ENABLED=True)
    def test_net_worth_uses_ledger_balances(self):
        Expense.objects.create(
            user=self.user,
            date=date.today(),
            amount=Decimal("150.00"),
            description="Groceries",
            category="Food",
            account=self.cash,
            currency="₹",
        )
        net_worth, base_balances = LedgerReadService.get_net_worth(self.user)
        self.assertEqual(net_worth, Decimal("850.00"))
        self.assertEqual(base_balances[self.cash.id], Decimal("850.00"))
