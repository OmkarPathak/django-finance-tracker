from datetime import timedelta, date

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class PaymentSource(models.Model):
    """
    Unified model for Bank Accounts, Digital Wallets, and Cash.
    Balance is deducted immediately when used for payments.
    """

    ACCOUNT_TYPE_CHOICES = [
        ("savings", "Savings Account"),
        ("current", "Current Account"),
        ("wallet", "Digital Wallet"),
        ("cash", "Cash in Hand"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_sources"
    )
    name = models.CharField(
        max_length=100
    )  # e.g., "Axis Savings", "Paytm Wallet", "Pocket Cash"
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    bank_name = models.CharField(
        max_length=100, blank=True, null=True
    )  # e.g., "Axis Bank", "Paytm"
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_payment_source_per_user",
            )
        ]
        ordering = ["account_type", "name"]

    def deduct(self, amount):
        """Deduct amount from balance."""
        self.balance -= amount
        self.save()

    def add(self, amount):
        """Add amount to balance (for refunds, deposits, etc.)."""
        self.balance += amount
        self.save()

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()}) - ₹{self.balance}"


class CreditCard(models.Model):
    """
    Credit Card model with billing cycle tracking.
    Tracks available limit and generates billing information.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="credit_cards"
    )
    name = models.CharField(
        max_length=100
    )  # e.g., "Axis Flipkart Card", "HDFC Regalia"
    bank_name = models.CharField(max_length=100)  # e.g., "Axis Bank", "HDFC"
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2)
    available_limit = models.DecimalField(max_digits=12, decimal_places=2)
    billing_cycle_day = models.PositiveIntegerField(
        help_text="Day of month when bill generates (1-28)"
    )
    due_date_days = models.PositiveIntegerField(
        default=20, help_text="Days after billing date to pay"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_credit_card_per_user",
            )
        ]
        ordering = ["bank_name", "name"]

    @property
    def used_limit(self):
        """Amount of credit used."""
        return self.credit_limit - self.available_limit

    @property
    def next_billing_date(self):
        """Calculate next billing date based on billing cycle day."""
        today = date.today()
        try:
            if today.day <= self.billing_cycle_day:
                return today.replace(day=self.billing_cycle_day)
            else:
                # Move to next month
                if today.month == 12:
                    return date(today.year + 1, 1, self.billing_cycle_day)
                else:
                    return date(today.year, today.month + 1, self.billing_cycle_day)
        except ValueError:
            # Handle months with fewer days (e.g., Feb 30)
            next_month = today.replace(day=1) + timedelta(days=32)
            last_day = (next_month.replace(day=1) - timedelta(days=1)).day
            return next_month.replace(day=min(self.billing_cycle_day, last_day))

    @property
    def next_due_date(self):
        """Calculate payment due date (billing date + due_date_days)."""
        return self.next_billing_date + timedelta(days=self.due_date_days)

    def use_credit(self, amount):
        """Use credit (reduce available limit)."""
        self.available_limit -= amount
        self.save()

    def pay_bill(self, amount):
        """Pay bill (restore available limit)."""
        self.available_limit = min(self.credit_limit, self.available_limit + amount)
        self.save()

    def __str__(self):
        return f"{self.name} ({self.bank_name}) - Available: ₹{self.available_limit}/{self.credit_limit}"


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    category = models.CharField(max_length=255)

    PAYMENT_OPTIONS = [
        ("Cash", "Cash"),
        ("Credit Card", "Credit Card"),
        ("Debit Card", "Debit Card"),
        ("UPI", "UPI"),
        ("NetBanking", "NetBanking"),
    ]
    payment_method = models.CharField(
        max_length=50, choices=PAYMENT_OPTIONS, default="Cash"
    )

    # Linked payment source (for bank accounts, wallets, cash tracking)
    payment_source = models.ForeignKey(
        PaymentSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        help_text="Bank account, wallet, or cash source used for this expense",
    )

    # Linked credit card (for credit card payments)
    credit_card = models.ForeignKey(
        CreditCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        help_text="Credit card used for this expense",
    )

    # Cashback fields
    has_cashback = models.BooleanField(default=False)
    CASHBACK_TYPE_CHOICES = [
        ("PERCENTAGE", "Percentage (%)"),
        ("FIXED", "Fixed Amount (₹)"),
    ]
    cashback_type = models.CharField(
        max_length=10, choices=CASHBACK_TYPE_CHOICES, blank=True, null=True
    )
    cashback_value = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def cashback_amount(self):
        """Calculate the actual cashback amount based on type and value."""
        if not self.has_cashback or not self.cashback_value:
            return 0

        if self.cashback_type == "PERCENTAGE":
            return (self.amount * self.cashback_value) / 100
        elif self.cashback_type == "FIXED":
            return self.cashback_value
        return 0

    @property
    def effective_amount(self):
        """Calculate the effective expense amount after applying cashback."""
        return self.amount - self.cashback_amount

    @property
    def user_share_amount(self):
        """
        Get the user's share for shared expenses.
        For regular expenses, returns the full amount.
        For shared expenses, returns only the user's share (0 if user is not a participant).
        """
        try:
            shared_details = self.shared_details
            # Find the user's share (participant with is_user=True)
            user_share = shared_details.shares.filter(participant__is_user=True).first()
            if user_share:
                return user_share.amount
            # If no user share found in a shared expense, user is not a participant (paid for friends only)
            return 0
        except SharedExpense.DoesNotExist:
            # Not a shared expense, return full amount
            return self.amount

    @property
    def user_effective_amount(self):
        """
        Get the user's effective share after applying cashback.
        For shared expenses, applies cashback proportionally to user's share.
        """
        user_share = self.user_share_amount
        if (
            not self.has_cashback
            or not self.cashback_value
            or user_share == self.amount
        ):
            # No cashback or full expense - use existing logic
            if user_share == self.amount:
                return self.effective_amount
            return user_share

        # Calculate proportional cashback for shared expense
        share_ratio = user_share / self.amount if self.amount else 0
        proportional_cashback = self.cashback_amount * share_ratio
        return user_share - proportional_cashback

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
                fields=["user", "date", "amount", "description", "category"],
                name="unique_expense",
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
    name = models.CharField(max_length=255)
    limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_category")
        ]

    def __str__(self):
        return self.name


class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=255)  # e.g. Salary, Freelance, Dividend
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.source:
            self.source = self.source.strip()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date", "amount", "source"], name="unique_income"
            )
        ]
        indexes = [
            models.Index(fields=['user', 'source']),
        ]

    def __str__(self):
        return f"{self.date} - {self.source} - {self.amount}"


class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = [
        ("DAILY", "Daily"),
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly"),
    ]
    TRANSACTION_TYPE_CHOICES = [
        ("EXPENSE", "Expense"),
        ("INCOME", "Income"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    category = models.CharField(max_length=255, blank=True, null=True)  # For Expense
    source = models.CharField(max_length=255, blank=True, null=True)  # For Income

    # We can reuse the PAYMENT_OPTIONS from Expense, or duplicate them.
    # Reusing is cleaner but requires referencing Expense.PAYMENT_OPTIONS or moving it to a constant.
    # Given the context, I'll access it via Expense.PAYMENT_OPTIONS if possible, or just duplicate for safety/decoupling if cleaner.
    # Let's duplicate to avoid circular dependency issues if models are rearranged, but actually they are in the same file.
    # Accessing Expense.PAYMENT_OPTIONS is fine.
    payment_method = models.CharField(
        max_length=50, choices=Expense.PAYMENT_OPTIONS, default="Cash"
    )

    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    last_processed_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def get_next_date(current_date, frequency):
        if frequency == "DAILY":
            return current_date + timedelta(days=1)
        elif frequency == "WEEKLY":
            return current_date + timedelta(weeks=1)
        elif frequency == "MONTHLY":
            month = current_date.month % 12 + 1
            year = current_date.year + (current_date.month // 12)
            try:
                return current_date.replace(year=year, month=month)
            except ValueError:
                # Handle Feb 29/30/31
                next_month = current_date + timedelta(days=31)
                return next_month.replace(day=1) - timedelta(days=1)
        elif frequency == "YEARLY":
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
        ("₹", "Indian Rupee (₹)"),
        ("$", "US Dollar ($)"),
        ("€", "Euro (€)"),
        ("£", "Pound Sterling (£)"),
        ("¥", "Japanese Yen (¥)"),
        ("A$", "Australian Dollar (A$)"),
        ("C$", "Canadian Dollar (C$)"),
        ("CHF", "Swiss Franc (CHF)"),
        ("元", "Chinese Yuan (元)"),
        ("₩", "South Korean Won (₩)"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="₹")
    has_seen_tutorial = models.BooleanField(default=False)

    # Subscription Fields
    TIER_CHOICES = [
        ("FREE", "Free"),
        ("PLUS", "Plus"),
        ("PRO", "Pro"),
    ]
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default="FREE")
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
    tier = models.CharField(max_length=10)  # PLUS, PRO
    status = models.CharField(
        max_length=20, default="PENDING"
    )  # PENDING, SUCCESS, FAILED
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.tier} - {self.status}"


class SubscriptionPlan(models.Model):
    TIER_CHOICES = [
        ("PLUS", "Plus"),
        ("PRO", "Pro"),
    ]
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Price in INR"
    )
    features = models.TextField(help_text="Comma separated features", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ₹{self.price}"


class Friend(models.Model):
    """
    Master table for friends/contacts that can be involved in shared expenses.
    Global list, reusable across all expenses.
    """

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friends")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_friend_per_user"
            )
        ]

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    @property
    def balance(self):
        """
        Calculate net balance with this friend.
        Positive = friend owes you, Negative = you owe friend.
        """
        from django.db.models import Sum

        # Amount friend owes you (you paid, friend participated)
        friend_owes = (
            Share.objects.filter(
                participant__friend=self,
                participant__is_payer=False,
                shared_expense__participants__is_user=True,
                shared_expense__participants__is_payer=True,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # Amount you owe friend (friend paid, you participated)
        you_owe = (
            Share.objects.filter(
                participant__is_user=True,
                participant__is_payer=False,
                shared_expense__participants__friend=self,
                shared_expense__participants__is_payer=True,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        return friend_owes - you_owe

    def get_transactions(self):
        """Get all shared expenses involving this friend."""
        return SharedExpense.objects.filter(participants__friend=self).distinct()

    def __str__(self):
        return self.name


class SharedExpense(models.Model):
    """
    Represents a shared expense that links to a base Expense and tracks
    which participant paid for it.
    """

    expense = models.OneToOneField(
        Expense, on_delete=models.CASCADE, related_name="shared_details"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def payer(self):
        """Get the participant who paid for this expense."""
        return self.participants.filter(is_payer=True).first()

    def get_friends_involved(self):
        """Get all friends involved in this expense."""
        return Friend.objects.filter(expense_participations__shared_expense=self)

    def __str__(self):
        payer = self.payer
        payer_name = payer.name if payer else "Unknown"
        return f"Shared: {self.expense.description} - Paid by {payer_name}"


class SharedExpenseParticipant(models.Model):
    """
    Links friends to shared expenses as participants.
    Populated from the Friend master table when creating transactions.
    """

    shared_expense = models.ForeignKey(
        SharedExpense, on_delete=models.CASCADE, related_name="participants"
    )
    friend = models.ForeignKey(
        Friend,
        on_delete=models.PROTECT,  # Prevent deletion if friend is used in transactions
        related_name="expense_participations",
        null=True,
        blank=True,
    )
    is_user = models.BooleanField(default=False)  # True = logged-in user (You)
    is_payer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def name(self):
        """Get participant name - 'You' for user, friend name otherwise."""
        if self.is_user:
            return "You"
        return self.friend.name if self.friend else "Unknown"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shared_expense", "friend"],
                name="unique_friend_per_shared_expense",
                condition=models.Q(friend__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["shared_expense", "is_user"],
                name="unique_user_per_shared_expense",
                condition=models.Q(is_user=True),
            ),
        ]

    def __str__(self):
        user_indicator = " (You)" if self.is_user else ""
        payer_indicator = " [Payer]" if self.is_payer else ""
        return f"{self.name}{user_indicator}{payer_indicator}"


class Share(models.Model):
    """
    Tracks each participant's share of a shared expense.
    """

    shared_expense = models.ForeignKey(
        SharedExpense, on_delete=models.CASCADE, related_name="shares"
    )
    participant = models.ForeignKey(
        SharedExpenseParticipant, on_delete=models.CASCADE, related_name="shares"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shared_expense", "participant"],
                name="unique_share_per_participant",
            ),
            models.CheckConstraint(
                check=models.Q(amount__gt=0), name="positive_share_amount"
            ),
        ]

    def __str__(self):
        return f"{self.participant.name}: ₹{self.amount}"

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
