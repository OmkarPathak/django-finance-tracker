from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.category:
            self.category = self.category.strip()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date', 'amount', 'description', 'category'],
                name='unique_expense'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'payment_method']),
        ]

    def __str__(self):
        return f"{self.date} - {self.description} - {self.amount}"

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=_('Category Name'))
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.source:
            self.source = self.source.strip()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date', 'amount', 'source'],
                name='unique_income'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'source']),
        ]

    def __str__(self):
        return f"{self.date} - {self.source} - {self.amount}"

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
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, verbose_name=_('Transaction Type'))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Amount'))
    description = models.TextField(verbose_name=_('Description'))
    category = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Category'))
    source = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Source'))
    
    payment_method = models.CharField(max_length=50, choices=Expense.PAYMENT_OPTIONS, default='Cash', verbose_name=_('Payment Method'))
    
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
        if not self.last_processed_date:
            return self.start_date
        return self.get_next_date(self.last_processed_date, self.frequency)

    def __str__(self):
        return f"{self.transaction_type} - {self.description} ({self.frequency})"
        
class UserProfile(models.Model):
    CURRENCY_CHOICES = [
        ('₹', 'Indian Rupee (₹)'),
        ('$', 'US Dollar ($)'),
        ('€', 'Euro (€)'),
        ('£', 'Pound Sterling (£)'),
        ('¥', 'Japanese Yen (¥)'),
        ('A$', 'Australian Dollar (A$)'),
        ('C$', 'Canadian Dollar (C$)'),
        ('CHF', 'Swiss Franc (CHF)'),
        ('元', 'Chinese Yuan (元)'),
        ('₩', 'South Korean Won (₩)'),
    ]

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

    @property
    def is_pro(self):
        """Check if user has active Pro access (either lifetime or valid subscription)."""
        if self.tier == 'PRO':
            if self.is_lifetime:
                return True
            if self.subscription_end_date and self.subscription_end_date > timezone.now():
                return True
        return False
    
    @property
    def is_plus(self):
        """Check if user has active Plus access (or higher)."""
        if self.tier in ['PLUS', 'PRO']:
            if self.is_lifetime:
                return True
            if self.subscription_end_date and self.subscription_end_date > timezone.now():
                return True
        return False

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.tier})"

class PaymentHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tier = models.CharField(max_length=10) # PLUS, PRO
    status = models.CharField(max_length=20, default='PENDING') # PENDING, SUCCESS, FAILED
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.tier} - {self.status}"

class SubscriptionPlan(models.Model):
    TIER_CHOICES = [
        ('PLUS', 'Plus'),
        ('PRO', 'Pro'),
    ]
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in INR")
    features = models.TextField(help_text="Comma separated features", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ₹{self.price}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optional link to the transaction that triggered it
    related_transaction = models.ForeignKey('RecurringTransaction', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
