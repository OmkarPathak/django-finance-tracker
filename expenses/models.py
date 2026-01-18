from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    category = models.CharField(max_length=255)
    
    PAYMENT_OPTIONS = [
        ('Cash', 'Cash'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('UPI', 'UPI'),
        ('NetBanking', 'NetBanking'),
    ]
    payment_method = models.CharField(max_length=50, choices=PAYMENT_OPTIONS, default='Cash')
    
    # Cashback fields
    has_cashback = models.BooleanField(default=False)
    CASHBACK_TYPE_CHOICES = [
        ('PERCENTAGE', 'Percentage (%)'),
        ('FIXED', 'Fixed Amount (₹)'),
    ]
    cashback_type = models.CharField(max_length=10, choices=CASHBACK_TYPE_CHOICES, blank=True, null=True)
    cashback_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def cashback_amount(self):
        """Calculate the actual cashback amount based on type and value."""
        if not self.has_cashback or not self.cashback_value:
            return 0
        
        if self.cashback_type == 'PERCENTAGE':
            return (self.amount * self.cashback_value) / 100
        elif self.cashback_type == 'FIXED':
            return self.cashback_value
        return 0
    
    @property
    def effective_amount(self):
        """Calculate the effective expense amount after applying cashback."""
        return self.amount - self.cashback_amount

    def save(self, *args, **kwargs):
        if self.category:
            self.category = self.category.strip()
        
        # Reset cashback fields if cashback is disabled
        if not self.has_cashback:
            self.cashback_type = None
            self.cashback_value = None
        
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date', 'amount', 'description', 'category'],
                name='unique_expense'
            )
        ]

    def __str__(self):
        return f"{self.date} - {self.description} - {self.amount}"

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

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
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=255) # e.g. Salary, Freelance, Dividend
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

    def __str__(self):
        return f"{self.date} - {self.source} - {self.amount}"

class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]
    TRANSACTION_TYPE_CHOICES = [
        ('EXPENSE', 'Expense'),
        ('INCOME', 'Income'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    category = models.CharField(max_length=255, blank=True, null=True) # For Expense
    source = models.CharField(max_length=255, blank=True, null=True)   # For Income
    
    # We can reuse the PAYMENT_OPTIONS from Expense, or duplicate them.
    # Reusing is cleaner but requires referencing Expense.PAYMENT_OPTIONS or moving it to a constant.
    # Given the context, I'll access it via Expense.PAYMENT_OPTIONS if possible, or just duplicate for safety/decoupling if cleaner.
    # Let's duplicate to avoid circular dependency issues if models are rearranged, but actually they are in the same file.
    # Accessing Expense.PAYMENT_OPTIONS is fine.
    payment_method = models.CharField(max_length=50, choices=Expense.PAYMENT_OPTIONS, default='Cash')
    
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
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

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='₹')
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
        # TEMPORARY: Unlock all features for free
        return True
        # from django.utils import timezone
        # if self.tier == 'PRO':
        #     if self.is_lifetime:
        #         return True
        #     if self.subscription_end_date and self.subscription_end_date > timezone.now():
        #         return True
        # return False
    
    @property
    def is_plus(self):
        """Check if user has active Plus access (or higher)."""
        # TEMPORARY: Unlock all features for free
        return True
        # from django.utils import timezone
        # if self.tier in ['PLUS', 'PRO']:
        #     if self.is_lifetime:
        #         return True
        #     if self.subscription_end_date and self.subscription_end_date > timezone.now():
        #         return True
        # return False

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


class SharedExpense(models.Model):
    """
    Represents a shared expense that links to a base Expense and tracks
    which participant paid for it.
    """
    expense = models.OneToOneField(
        Expense, 
        on_delete=models.CASCADE, 
        related_name='shared_details'
    )
    payer = models.ForeignKey(
        'Participant', 
        on_delete=models.PROTECT, 
        related_name='paid_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shared: {self.expense.description} - Paid by {self.payer.name}"


class Participant(models.Model):
    """
    Represents a person involved in a shared expense.
    """
    shared_expense = models.ForeignKey(
        SharedExpense, 
        on_delete=models.CASCADE, 
        related_name='participants'
    )
    name = models.CharField(max_length=255)
    is_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Trim whitespace from participant names
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['shared_expense', 'name'],
                name='unique_participant_per_expense'
            )
        ]

    def __str__(self):
        user_indicator = " (User)" if self.is_user else ""
        return f"{self.name}{user_indicator}"


class Share(models.Model):
    """
    Tracks each participant's share of a shared expense.
    """
    shared_expense = models.ForeignKey(
        SharedExpense, 
        on_delete=models.CASCADE, 
        related_name='shares'
    )
    participant = models.ForeignKey(
        Participant, 
        on_delete=models.CASCADE, 
        related_name='shares'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['shared_expense', 'participant'],
                name='unique_share_per_participant'
            ),
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='positive_share_amount'
            )
        ]

    def __str__(self):
        return f"{self.participant.name}: ₹{self.amount}"
