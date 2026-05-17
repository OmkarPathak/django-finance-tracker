import logging
import random
from decimal import Decimal

from django.conf import settings

from .ledger_rollout import is_user_in_read_cohort
from .models import JournalEntry, JournalLine
from .utils import get_exchange_rate

logger = logging.getLogger(__name__)


class LedgerReadService:
    @staticmethod
    def is_enabled(user=None):
        if user is None:
            return getattr(settings, "LEDGER_READ_ENABLED", False)
        return is_user_in_read_cohort(user)

    @staticmethod
    def _compare_logging_enabled():
        return getattr(settings, "LEDGER_READ_COMPARE_ENABLED", False)

    @staticmethod
    def _compare_sample_rate():
        try:
            return float(getattr(settings, "LEDGER_READ_COMPARE_SAMPLE_RATE", 1.0))
        except (TypeError, ValueError):
            return 1.0

    @classmethod
    def _log_comparison(cls, *, account, selected_balance, ledger_delta, used_fallback, has_opening_entry):
        if not cls._compare_logging_enabled():
            return
        if random.random() > max(0.0, min(1.0, cls._compare_sample_rate())):
            return

        logger.info(
            "ledger_read_compare",
            extra={
                "user_id": account.user_id,
                "account_id": account.id,
                "account_currency": account.currency,
                "model_balance": str(account.balance),
                "ledger_delta": str(ledger_delta),
                "selected_balance": str(selected_balance),
                "used_fallback": used_fallback,
                "has_opening_entry": has_opening_entry,
            },
        )

    @classmethod
    def _line_amount_in_account_currency(cls, line, account):
        if line.currency == account.currency:
            return line.amount
        rate = get_exchange_rate(line.currency, account.currency)
        return (line.amount * rate).quantize(Decimal("0.01"))

    @classmethod
    def get_account_ledger_delta(cls, account):
        lines = JournalLine.objects.filter(
            account_ref=account,
            journal_entry__status="POSTED",
        ).only("direction", "amount", "currency")

        if not lines.exists():
            return Decimal("0.00")

        debit = Decimal("0.00")
        credit = Decimal("0.00")
        for line in lines:
            converted = cls._line_amount_in_account_currency(line, account)
            if line.direction == "DEBIT":
                debit += converted
            else:
                credit += converted

        return (debit - credit).quantize(Decimal("0.01"))

    @classmethod
    def get_account_balance(cls, account):
        if not cls.is_enabled(account.user):
            return account.balance

        # Until opening balances are explicitly journaled during backfill,
        # fallback to model balance to avoid regressions for existing accounts.
        has_opening_entry = JournalEntry.objects.filter(
            user=account.user,
            source_type="ADJUSTMENT",
            metadata__opening_account_id=account.id,
            status="POSTED",
        ).exists()

        ledger_delta = cls.get_account_ledger_delta(account)

        if not has_opening_entry:
            cls._log_comparison(
                account=account,
                selected_balance=account.balance,
                ledger_delta=ledger_delta,
                used_fallback=True,
                has_opening_entry=False,
            )
            return account.balance

        selected = ledger_delta.quantize(Decimal("0.01"))
        cls._log_comparison(
            account=account,
            selected_balance=selected,
            ledger_delta=ledger_delta,
            used_fallback=False,
            has_opening_entry=True,
        )
        return selected

    @classmethod
    def get_net_worth(cls, user):
        accounts = user.accounts.filter(is_active=True)
        base_currency = user.profile.currency

        net_worth = Decimal("0.00")
        account_base_balances = {}

        for account in accounts:
            balance = cls.get_account_balance(account)
            if account.currency == base_currency:
                converted = balance
            else:
                rate = get_exchange_rate(account.currency, base_currency)
                converted = (balance * rate).quantize(Decimal("0.01"))
            account_base_balances[account.pk] = converted
            net_worth += converted

        return net_worth.quantize(Decimal("0.01")), account_base_balances
