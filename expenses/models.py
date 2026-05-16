from datetime import timedelta, date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from finance_tracker.plans import get_limit

from .utils import get_exchange_rate

CURRENCY_CHOICES = [
    ('₹', _('Indian Rupee (₹)')),
    ('$', _('US Dollar ($)')),
    ('€', _('Euro (€)')),
    ('£', _('Pound Sterling (£)')),
    ('¥', _('Japanese Yen (¥)')),
    ('A$', _('Australian Dollar (A$)')),
    ('C$', _('Canadian Dollar (C$)')),
    ('CHF', _('Swiss Franc (CHF)')),
    ('元', _('Chinese Yuan (元)')),
    ('₩', _('South Korean Won (₩)')),
]

class FinanceBaseManager(models.Manager):
    def get_monthly_summary(self, user, year, month):
        return self.filter(
            user=user, 
            date__year=year, 
            date__month=month
        ).aggregate(
            total=models.Sum('base_amount'),
            count=models.Count('id')
        )

class ExpenseManager(FinanceBaseManager):
    def get_queryset(self):
        return super().get_queryset().select_related('account')

    def get_category_breakdown(self, user, year, month):
        return self.filter(
            user=user, 
            date__year=year, 
            date__month=month
        ).values('category').annotate(
            total=models.Sum('base_amount')
        ).order_by('-total')

class IncomeManager(FinanceBaseManager):
    def get_queryset(self):
        return super().get_queryset().select_related('account')


class TransferManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('from_account', 'to_account')


class GoalContributionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('goal', 'account')


class Account(models.Model):
    ACCOUNT_TYPES = [
        ('CASH', _('Cash')),
        ('BANK', _('Bank Account')),
        ('CREDIT_CARD', _('Credit Card')),
        ('INVESTMENT', _('Investment Account')),
        ('FIXED_DEPOSIT', _('Fixed Deposit')),
        ('OTHER', _('Other')),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100, verbose_name=_('Account Name'))
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='BANK', verbose_name=_('Account Type'))
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Current Balance'))
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹', verbose_name=_('Currency'))
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_account_per_user')
        ]

    def __str__(self):
        return f"{self.name} ({self.currency}{self.balance})"

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(verbose_name=_('Date'))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Amount'))
    description = models.TextField(verbose_name=_('Description'))
    category = models.CharField(max_length=255, verbose_name=_('Category'))
    
    PAYMENT_OPTIONS = [
        ('Cash', _('Cash')),
        ('Credit Card', _('Credit Card')),
        ('Debit Card', _('Debit Card')),
        ('UPI', _('UPI')),
        ('NetBanking', _('NetBanking')),
    ]
    payment_method = models.CharField(max_length=50, choices=PAYMENT_OPTIONS, default='Cash', verbose_name=_('Payment Method'))
    
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹', verbose_name=_('Currency'))
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=1.0, verbose_name=_('Exchange Rate'))
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name=_('Amount in Base Currency'))

    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses', verbose_name=_('Account'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ExpenseManager()

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Handle balance reversal for updates
            if self.pk:
                old_instance = Expense.objects.select_related('account').select_for_update().get(pk=self.pk)
                if old_instance.account:
                    old_account = Account.objects.select_for_update().get(pk=old_instance.account_id)
                    # Convert old amount to account currency for reversal
                    reversal_amount = old_instance.amount
                    if old_instance.currency != old_instance.account.currency:
                        rate = get_exchange_rate(old_instance.currency, old_instance.account.currency)
                        reversal_amount = (old_instance.amount * rate).quantize(Decimal('0.01'))
                    
                    old_account.balance += reversal_amount
                    old_account.save(update_fields=['balance', 'updated_at'])

            if self.category:
                self.category = self.category.strip()
            
            # Multi-currency normalization
            base_currency = self.user.profile.currency
            if self.currency == base_currency:
                self.exchange_rate = Decimal('1.0')
                self.base_amount = self.amount
            else:
                self.exchange_rate = get_exchange_rate(self.currency, base_currency)
                self.base_amount = (self.amount * self.exchange_rate).quantize(Decimal('0.01'))
                
            super().save(*args, **kwargs)
            
            # Apply new balance
            if self.account:
                locked_account = Account.objects.select_for_update().get(pk=self.account_id)
                # Convert current amount to account currency
                apply_amount = self.amount
                if self.currency != locked_account.currency:
                    rate = get_exchange_rate(self.currency, locked_account.currency)
                    apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                
                locked_account.balance -= apply_amount
                locked_account.save(update_fields=['balance', 'updated_at'])

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.account:
                locked_account = Account.objects.select_for_update().get(pk=self.account_id)
                # Convert to account currency for deletion reversal
                apply_amount = self.amount
                if self.currency != locked_account.currency:
                    rate = get_exchange_rate(self.currency, locked_account.currency)
                    apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                
                locked_account.balance += apply_amount
                locked_account.save(update_fields=['balance', 'updated_at'])
            super().delete(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date', 'amount', 'currency', 'description', 'category'],
                name='unique_expense'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'payment_method']),
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f"{self.date} - {self.description} - {self.amount}"

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=_('Category Name'))
    icon = models.CharField(max_length=50, default='bi-tag', verbose_name=_('Icon'))
    limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_('Monthly Limit'))

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Categories'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_category'
            )
        ]

    def __str__(self):
        return self.name

class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(verbose_name=_('Date'))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Amount'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    source = models.CharField(max_length=255, verbose_name=_('Source')) # e.g. Salary, Freelance, Dividend
    
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹', verbose_name=_('Currency'))
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=1.0, verbose_name=_('Exchange Rate'))
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name=_('Amount in Base Currency'))

    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='incomes', verbose_name=_('Account'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = IncomeManager()

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Handle balance reversal for updates
            if self.pk:
                old_instance = Income.objects.select_related('account').select_for_update().get(pk=self.pk)
                if old_instance.account:
                    old_account = Account.objects.select_for_update().get(pk=old_instance.account_id)
                    # Convert to account currency for reversal
                    reversal_amount = old_instance.amount
                    if old_instance.currency != old_instance.account.currency:
                        rate = get_exchange_rate(old_instance.currency, old_instance.account.currency)
                        reversal_amount = (old_instance.amount * rate).quantize(Decimal('0.01'))
                    
                    old_account.balance -= reversal_amount
                    old_account.save(update_fields=['balance', 'updated_at'])

            if self.source:
                self.source = self.source.strip()
                
            # Multi-currency normalization
            base_currency = self.user.profile.currency
            if self.currency == base_currency:
                self.exchange_rate = Decimal('1.0')
                self.base_amount = self.amount
            else:
                self.exchange_rate = get_exchange_rate(self.currency, base_currency)
                self.base_amount = (self.amount * self.exchange_rate).quantize(Decimal('0.01'))

            super().save(*args, **kwargs)

            # Apply new balance
            if self.account:
                locked_account = Account.objects.select_for_update().get(pk=self.account_id)
                # Convert to account currency
                apply_amount = self.amount
                if self.currency != locked_account.currency:
                    rate = get_exchange_rate(self.currency, locked_account.currency)
                    apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                    
                locked_account.balance += apply_amount
                locked_account.save(update_fields=['balance', 'updated_at'])

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.account:
                locked_account = Account.objects.select_for_update().get(pk=self.account_id)
                # Convert to account currency for deletion reversal
                apply_amount = self.amount
                if self.currency != locked_account.currency:
                    rate = get_exchange_rate(self.currency, locked_account.currency)
                    apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                
                locked_account.balance -= apply_amount
                locked_account.save(update_fields=['balance', 'updated_at'])
            super().delete(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date', 'amount', 'currency', 'source'],
                name='unique_income'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'source']),
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f"{self.date} - {self.source} - {self.amount}"

class Transfer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    from_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transfers_out', verbose_name=_('From Account'))
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transfers_in', verbose_name=_('To Account'))
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'))
    date = models.DateField(default=timezone.now, verbose_name=_('Date'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    
    objects = TransferManager()
    
    # Multi-currency support (No currency field in DB yet for Transfer, using from_account.currency)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=1.0, verbose_name=_('Exchange Rate'))
    converted_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name=_('Amount in Base Currency'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.from_account_id and self.to_account_id and self.from_account_id == self.to_account_id:
            raise ValidationError({'to_account': _('Source and destination accounts must be different.')})

        if self.user_id and self.from_account and self.from_account.user_id != self.user_id:
            raise ValidationError({'from_account': _('From account must belong to the current user.')})

        if self.user_id and self.to_account and self.to_account.user_id != self.user_id:
            raise ValidationError({'to_account': _('To account must belong to the current user.')})

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            # Revert-and-Apply pattern for updates
            if self.pk:
                old_instance = Transfer.objects.select_related('from_account', 'to_account').select_for_update().get(pk=self.pk)
                old_from_account = Account.objects.select_for_update().get(pk=old_instance.from_account_id)
                old_to_account = Account.objects.select_for_update().get(pk=old_instance.to_account_id)
                # Revert old
                old_from_account.balance += old_instance.amount
                old_from_account.save(update_fields=['balance', 'updated_at'])
                
                # Convert from_account's amount to to_account's currency for reversal
                reversal_to_amount = old_instance.amount
                if old_instance.from_account.currency != old_instance.to_account.currency:
                    rate = get_exchange_rate(old_instance.from_account.currency, old_instance.to_account.currency)
                    reversal_to_amount = (old_instance.amount * rate).quantize(Decimal('0.01'))
                
                old_to_account.balance -= reversal_to_amount
                old_to_account.save(update_fields=['balance', 'updated_at'])

            # Multi-currency normalization (Transfers use the currency of the from_account usually)
            currency = self.from_account.currency
                
            base_currency = self.user.profile.currency
            if currency == base_currency:
                self.exchange_rate = Decimal('1.0')
                self.converted_amount = self.amount
            else:
                self.exchange_rate = get_exchange_rate(currency, base_currency)
                self.converted_amount = (self.amount * self.exchange_rate).quantize(Decimal('0.01'))

            super().save(*args, **kwargs)

            # Apply new
            from_account = Account.objects.select_for_update().get(pk=self.from_account_id)
            to_account = Account.objects.select_for_update().get(pk=self.to_account_id)
            
            from_account.balance -= self.amount # amount is in from_account currency
            from_account.save(update_fields=['balance', 'updated_at'])
            
            # Convert to to_account currency
            to_apply_amount = self.amount
            if from_account.currency != to_account.currency:
                rate = get_exchange_rate(from_account.currency, to_account.currency)
                to_apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                
            to_account.balance += to_apply_amount
            to_account.save(update_fields=['balance', 'updated_at'])

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            from_account = Account.objects.select_for_update().get(pk=self.from_account_id)
            to_account = Account.objects.select_for_update().get(pk=self.to_account_id)
            from_account.balance += self.amount
            from_account.save(update_fields=['balance', 'updated_at'])
            
            # Convert for reversal
            to_revert_amount = self.amount
            if from_account.currency != to_account.currency:
                rate = get_exchange_rate(from_account.currency, to_account.currency)
                to_revert_amount = (self.amount * rate).quantize(Decimal('0.01'))
                
            to_account.balance -= to_revert_amount
            to_account.save(update_fields=['balance', 'updated_at'])
            super().delete(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~models.Q(from_account=models.F('to_account')),
                name='transfer_accounts_must_differ',
            )
        ]

    def __str__(self):
        return f"{self.date} - Transfer {self.amount} from {self.from_account.name} to {self.to_account.name}"

class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', _('Daily')),
        ('WEEKLY', _('Weekly')),
        ('MONTHLY', _('Monthly')),
        ('YEARLY', _('Yearly')),
    ]
    TRANSACTION_TYPE_CHOICES = [
        ('EXPENSE', _('Expense')),
        ('INCOME', _('Income')),
        ('TRANSFER', _('Transfer')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, verbose_name=_('Transaction Type'))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Amount'))
    description = models.TextField(verbose_name=_('Description'))
    category = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Category'))
    source = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Source'))
    
    payment_method = models.CharField(max_length=50, choices=Expense.PAYMENT_OPTIONS, default='Cash', verbose_name=_('Payment Method'))
    
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹', verbose_name=_('Currency'))
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=1.0, verbose_name=_('Exchange Rate'))
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name=_('Amount in Base Currency'))

    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Account'))

    # Transfer-specific fields
    from_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_transfers_out', verbose_name=_('From Account'))
    to_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_transfers_in', verbose_name=_('To Account'))

    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, verbose_name=_('Frequency'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    last_processed_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def get_next_date(current_date, frequency):
        if frequency == 'DAILY':
            return current_date + timedelta(days=1)
        elif frequency == 'WEEKLY':
            return current_date + timedelta(weeks=1)
        elif frequency == 'MONTHLY':
            month = current_date.month % 12 + 1
            year = current_date.year + (current_date.month // 12)
            try:
                return current_date.replace(year=year, month=month)
            except ValueError:
                # Handle Feb 29/30/31
                next_month = current_date + timedelta(days=31)
                return next_month.replace(day=1) - timedelta(days=1)
        elif frequency == 'YEARLY':
            try:
                return current_date.replace(year=current_date.year + 1)
            except ValueError:
                return current_date.replace(year=current_date.year + 1, month=2, day=28)
        return current_date + timedelta(days=365)

    @property
    def next_due_date(self):
        if not self.last_processed_date or self.last_processed_date < self.start_date:
            return self.start_date

        if self.frequency == 'DAILY':
            return self.last_processed_date + timedelta(days=1)
            
        elif self.frequency == 'WEEKLY':
            target = self.last_processed_date + timedelta(days=1)
            days_ahead = (self.start_date.weekday() - target.weekday()) % 7
            return target + timedelta(days=days_ahead)
            
        elif self.frequency == 'MONTHLY':
            target = self.last_processed_date + timedelta(days=1)
            month = target.month
            year = target.year
            
            if target.day > self.start_date.day:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                    
            while True:
                try:
                    return date(year, month, self.start_date.day)
                except ValueError:
                    if month == 12:
                        return date(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        return date(year, month + 1, 1) - timedelta(days=1)

        elif self.frequency == 'YEARLY':
            target = self.last_processed_date + timedelta(days=1)
            year = target.year
            if (target.month, target.day) > (self.start_date.month, self.start_date.day):
                year += 1
            try:
                return date(year, self.start_date.month, self.start_date.day)
            except ValueError:
                return date(year, 2, 28)
                
        return self.get_next_date(self.last_processed_date, self.frequency)

    def save(self, *args, **kwargs):
        # Multi-currency normalization
        base_currency = self.user.profile.currency
        if self.currency == base_currency:
            self.exchange_rate = Decimal('1.0')
            self.base_amount = self.amount
        else:
            self.exchange_rate = get_exchange_rate(self.currency, base_currency)
            self.base_amount = (self.amount * self.exchange_rate).quantize(Decimal('0.01'))
            
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'transaction_type', 'amount', 'currency', 'description', 'frequency', 'start_date'],
                name='unique_recurring_transaction'
            )
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.description} ({self.frequency})"
        
class UserProfile(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('mr', 'Marathi'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹')
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    has_seen_tutorial = models.BooleanField(default=False)

    # Subscription Fields
    TIER_CHOICES = [
        ('FREE', 'Free'),
        ('PLUS', 'Plus'),
        ('PRO', 'Pro'),
    ]
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='FREE')
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    is_lifetime = models.BooleanField(default=False)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_customer_id = models.CharField(max_length=100, blank=True, null=True)
    cancel_at_cycle_end = models.BooleanField(default=False)
    has_used_trial = models.BooleanField(default=False)

    # Lifecycle email drip tracking
    last_drip_email_day = models.IntegerField(default=0)
    expiry_reminder_sent = models.BooleanField(default=False)
    daily_reminder = models.BooleanField(default=True, verbose_name=_('Daily Expense Reminder'))

    @property
    def is_pro(self):
        """Check if user has active Pro access (either lifetime or valid subscription)."""
        if self.tier == 'PRO':
            if self.is_lifetime:
                return True
            if not self.subscription_end_date:
                return True
            if self.subscription_end_date > timezone.now():
                return True
        return False
    
    @property
    def is_plus(self):
        """Check if user has active Plus access (or higher)."""
        if self.tier in ['PLUS', 'PRO']:
            if self.is_lifetime:
                return True
            if not self.subscription_end_date:
                return True # Assume active if no end date set manually
            if self.subscription_end_date > timezone.now():
                return True
        return False

    @property
    def has_net_worth_access(self):
        """Net worth is a paid feature."""
        return get_limit(self.active_tier, 'net_worth')

    def can_add_account(self):
        """Checks account limit based on tier."""
        limit = get_limit(self.active_tier, 'accounts')
        if limit == -1: return True
        return self.user.accounts.filter(is_active=True).count() < limit

    def can_add_expense(self):
        """Checks monthly expense limit based on tier."""
        limit = get_limit(self.active_tier, 'expenses_per_month')
        if limit == -1: return True
        
        now = timezone.now()
        month_count = Expense.objects.filter(
            user=self.user, 
            date__year=now.year, 
            date__month=now.month
        ).count()
        return month_count < limit

    def can_add_recurring(self):
        """Checks recurring transaction limit based on tier."""
        limit = get_limit(self.active_tier, 'recurring_transactions')
        if limit == -1: return True
        return self.user.recurringtransaction_set.filter(is_active=True).count() < limit

    def can_add_category(self):
        """Checks category limit based on tier."""
        limit = get_limit(self.active_tier, 'budget_categories')
        if limit == -1: return True
        return self.user.category_set.count() < limit

    def can_add_goal(self):
        """Checks savings goal limit based on tier."""
        limit = get_limit(self.active_tier, 'savings_goals')
        if limit == -1: return True
        return self.user.savings_goals.count() < limit

    def is_recurring_locked(self, obj):
        """Check if a specific recurring transaction is locked based on tier limits."""
        limit = get_limit(self.active_tier, 'recurring_transactions')
        if limit == -1: return False
        
        subs = list(self.user.recurringtransaction_set.all().order_by('created_at', 'id'))
        if obj in subs and subs.index(obj) >= limit:
            return True
        return False

    def is_account_locked(self, account):
        """Check if a specific account is locked based on tier limits."""
        limit = get_limit(self.active_tier, 'accounts')
        if limit == -1: return False
        
        # Order by created_at so the 'oldest' accounts stay unlocked
        accounts = list(self.user.accounts.filter(is_active=True).order_by('created_at', 'id'))
        if account in accounts and accounts.index(account) >= limit:
            return True
        return False

    @property
    def active_tier(self):
        """Returns the actual active tier string (respecting subscription expiry)."""
        if self.is_pro:
            return 'PRO'
        if self.is_plus:
            return 'PLUS'
        return 'FREE'
    
    @property
    def can_export_csv(self):
        """Checks if CSV export is allowed for the user's tier."""
        from finance_tracker.plans import get_limit
        return get_limit(self.active_tier, 'export_csv')

    @property
    def has_ai_access(self):
        """Checks if AI insights is allowed for the user's tier."""
        from finance_tracker.plans import get_limit
        return get_limit(self.active_tier, 'ai_insights')

    @property
    def net_worth_history_limit(self):
        """Returns the number of months of net worth history allowed for the user's tier."""
        from finance_tracker.plans import get_limit
        return get_limit(self.active_tier, 'net_worth_history')

    @property
    def active_tier_display(self):
        """Returns the actual active tier display name (respecting subscription expiry)."""
        tier = self.active_tier
        return dict(self.TIER_CHOICES).get(tier, 'Free')

    @property
    def subscription_expired(self):
        """Check if the user was on a paid tier but it has now expired."""
        if self.tier in ['PRO', 'PLUS'] and self.active_tier == 'FREE':
            if self.subscription_end_date and self.subscription_end_date < timezone.now():
                return True
        return False

    @property
    def last_tier_display(self):
        """Returns the display name of the tier the user was on before expiry."""
        return dict(self.TIER_CHOICES).get(self.tier, 'Pro')

    @property
    def can_start_trial(self):
        """Check if user is eligible to start a free 7-day Pro trial."""
        return self.tier == 'FREE' and not self.has_used_trial

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.tier})"

class PaymentHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tier = models.CharField(max_length=10) # PLUS, PRO
    duration = models.CharField(max_length=10, default='YEARLY')  # MONTHLY, YEARLY
    status = models.CharField(max_length=20, default='PENDING') # PENDING, SUCCESS, FAILED
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.tier} ({self.duration}) - {self.status}"

class SubscriptionPlan(models.Model):
    DURATION_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]
    TIER_CHOICES = [
        ('PLUS', 'Plus'),
        ('PRO', 'Pro'),
    ]
    tier = models.CharField(max_length=10, choices=TIER_CHOICES)
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES, default='YEARLY')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in INR")
    razorpay_plan_id = models.CharField(max_length=100, blank=True, null=True)
    features = models.TextField(help_text="Comma separated features", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tier', 'duration'],
                name='unique_plan_tier_duration'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_duration_display()}) - ₹{self.price}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('RECURRING', _('Recurring Transaction')),
        ('ANALYTICS', _('AI Analytics/Insights')),
        ('MILESTONE', _('Financial Milestone')),
        ('SYSTEM', _('System/Subscription Alert')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='SYSTEM')
    slug = models.CharField(max_length=255, null=True, blank=True, help_text=_("Used for deduplication (same slug shouldn't repeat in a month)"))
    link = models.CharField(max_length=500, null=True, blank=True, help_text=_("URL for redirection when clicked"))
    metadata = models.JSONField(null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optional link to the transaction that triggered it
    related_transaction = models.ForeignKey('RecurringTransaction', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title} ({self.notification_type})"

class SavingsGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(max_length=255, verbose_name=_('Goal Name'))
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Target Amount'))
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Current Amount'))
    target_date = models.DateField(blank=True, null=True, verbose_name=_('Target Date'))
    icon = models.CharField(max_length=10, default='🎯', verbose_name=_('Icon'))
    color = models.CharField(max_length=20, default='primary', verbose_name=_('Color Theme'))
    is_completed = models.BooleanField(default=False)
    
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹', verbose_name=_('Currency'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def progress_percentage(self):
        if self.target_amount > 0:
            percentage = (self.current_amount / self.target_amount) * 100
            if percentage > 100:
                return 100
            return round(percentage, 1)
        return 0
        
    def save(self, *args, **kwargs):
        if self.current_amount >= self.target_amount and self.target_amount > 0:
            self.is_completed = True
        else:
            self.is_completed = False
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            # Before deleting the goal, we must refund all contributions to their respective accounts
            # Django's cascade delete does not call individual delete() methods on related objects,
            # so we manually iterate to ensure account balances are restored.
            for contribution in self.contributions.select_related('account').all():
                if contribution.account:
                    contribution.account.balance += contribution.amount
                    contribution.account.save()
            super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

class GoalContribution(models.Model):
    goal = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name='contributions')
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='goal_contributions', verbose_name=_('From Account'))
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Contribution Amount'))
    date = models.DateField(default=timezone.now, verbose_name=_('Date'))
    
    created_at = models.DateTimeField(auto_now_add=True)

    objects = GoalContributionManager()

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                old_instance = GoalContribution.objects.select_related('account', 'goal').select_for_update().get(pk=self.pk)
                # Revert old balance and goal amount
                if old_instance.account:
                    old_account = Account.objects.select_for_update().get(pk=old_instance.account_id)
                    # Convert goal currency to account currency for reversal
                    reversal_amount = old_instance.amount
                    if old_instance.goal.currency != old_instance.account.currency:
                        rate = get_exchange_rate(old_instance.goal.currency, old_instance.account.currency)
                        reversal_amount = (old_instance.amount * rate).quantize(Decimal('0.01'))
                        
                    old_account.balance += reversal_amount
                    old_account.save(update_fields=['balance', 'updated_at'])
                self.goal.current_amount -= old_instance.amount
            
            super().save(*args, **kwargs)
            
            # Apply new balance and goal amount
            if self.account:
                locked_account = Account.objects.select_for_update().get(pk=self.account_id)
                # Convert goal currency to account currency
                apply_amount = self.amount
                if self.goal.currency != locked_account.currency:
                    rate = get_exchange_rate(self.goal.currency, locked_account.currency)
                    apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                
                locked_account.balance -= apply_amount
                locked_account.save(update_fields=['balance', 'updated_at'])
            
            self.goal.current_amount += self.amount
            self.goal.save()
            
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            # Update account balance and goal's current amount when deleting a contribution
            if self.account:
                locked_account = Account.objects.select_for_update().get(pk=self.account_id)
                # Convert for deletion reversal
                apply_amount = self.amount
                if self.goal.currency != locked_account.currency:
                    rate = get_exchange_rate(self.goal.currency, locked_account.currency)
                    apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                    
                locked_account.balance += apply_amount
                locked_account.save(update_fields=['balance', 'updated_at'])
                
            self.goal.current_amount -= self.amount
            self.goal.save()
            
            super().delete(*args, **kwargs)

    def __str__(self):
        return f"+{self.amount} to {self.goal.name} on {self.date}"

class EmailLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='email_logs')
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    html_body = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='SENT') # SENT, FAILED
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.to_email}: {self.subject}"

class Loan(models.Model):
    LOAN_TYPES = [
        ('HOME', _('Home Loan')),
        ('CAR', _('Car Loan')),
        ('PERSONAL', _('Personal Loan')),
        ('EDUCATION', _('Education Loan')),
        ('BUSINESS', _('Business Loan')),
        ('OTHER', _('Other')),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    name = models.CharField(max_length=100, verbose_name=_('Loan Name'))
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES, default='HOME', verbose_name=_('Loan Type'))
    initial_principal = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('Initial Principal Amount'))
    duration_months = models.IntegerField(verbose_name=_('Duration (Months)'))
    start_date = models.DateField(default=timezone.now, verbose_name=_('Start Date'))
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹', verbose_name=_('Currency'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.initial_principal} {self.currency}"

class LoanInterestRate(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='interest_rates')
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_('Annual Interest Rate (%)'))
    effective_date = models.DateField(default=timezone.now, verbose_name=_('Effective Date'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.loan.name} - {self.interest_rate}% from {self.effective_date}"

class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    from_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='loan_repayments', verbose_name=_('Paid From Account'))
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Total Amount Paid (EMI)'))
    principal_portion = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Principal Portion'))
    interest_portion = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Interest Portion'))
    date = models.DateField(default=timezone.now, verbose_name=_('Payment Date'))
    
    # Multi-currency support
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=1.0, verbose_name=_('Exchange Rate'))
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name=_('Amount in Base Currency'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.loan.name} Repayment - {self.amount} on {self.date}"

    def clean(self):
        if self.amount is None or self.amount <= 0:
            raise ValidationError({'amount': _('Repayment amount must be greater than zero.')})

        if self.principal_portion is None or self.principal_portion < 0:
            raise ValidationError({'principal_portion': _('Principal portion cannot be negative.')})

        if self.interest_portion is None or self.interest_portion < 0:
            raise ValidationError({'interest_portion': _('Interest portion cannot be negative.')})

        if (self.principal_portion + self.interest_portion).quantize(Decimal('0.01')) != self.amount.quantize(Decimal('0.01')):
            raise ValidationError(_('Repayment must equal principal portion plus interest portion.'))

        if self.from_account and self.from_account.user_id != self.loan.user_id:
            raise ValidationError({'from_account': _('Selected account does not belong to this user.')})

        prior_paid = self.loan.repayments.exclude(pk=self.pk).aggregate(
            total_principal=models.Sum('principal_portion')
        )['total_principal'] or Decimal('0.00')
        remaining_principal = self.loan.initial_principal - prior_paid
        if self.principal_portion > remaining_principal:
            raise ValidationError({'principal_portion': _('Principal portion cannot exceed remaining principal.')})

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            # Handle balance reversal for updates
            if self.pk:
                old_instance = LoanRepayment.objects.select_related('from_account', 'loan').select_for_update().get(pk=self.pk)
                if old_instance.from_account:
                    old_account = Account.objects.select_for_update().get(pk=old_instance.from_account_id)
                    # Convert old amount to account currency for reversal
                    reversal_amount = old_instance.amount
                    if old_instance.loan.currency != old_instance.from_account.currency:
                        rate = get_exchange_rate(old_instance.loan.currency, old_instance.from_account.currency)
                        reversal_amount = (old_instance.amount * rate).quantize(Decimal('0.01'))
                    
                    old_account.balance += reversal_amount
                    old_account.save(update_fields=['balance', 'updated_at'])

            # Multi-currency normalization (amount is in loan currency)
            base_currency = self.loan.user.profile.currency
            if self.loan.currency == base_currency:
                self.exchange_rate = Decimal('1.0')
                self.base_amount = self.amount
            else:
                self.exchange_rate = get_exchange_rate(self.loan.currency, base_currency)
                self.base_amount = (self.amount * self.exchange_rate).quantize(Decimal('0.01'))

            super().save(*args, **kwargs)

            # Apply new balance
            if self.from_account:
                locked_account = Account.objects.select_for_update().get(pk=self.from_account_id)
                # Convert current amount to account currency
                apply_amount = self.amount
                if self.loan.currency != locked_account.currency:
                    rate = get_exchange_rate(self.loan.currency, locked_account.currency)
                    apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                
                locked_account.balance -= apply_amount
                locked_account.save(update_fields=['balance', 'updated_at'])

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.from_account:
                locked_account = Account.objects.select_for_update().get(pk=self.from_account_id)
                # Convert to account currency for deletion reversal
                apply_amount = self.amount
                if self.loan.currency != locked_account.currency:
                    rate = get_exchange_rate(self.loan.currency, locked_account.currency)
                    apply_amount = (self.amount * rate).quantize(Decimal('0.01'))
                
                locked_account.balance += apply_amount
                locked_account.save(update_fields=['balance', 'updated_at'])
            super().delete(*args, **kwargs)

