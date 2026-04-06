from django.contrib import admin

from .models import (
    Account,
    Category,
    Expense,
    Income,
    Notification,
    RecurringTransaction,
    Transfer,
    EmailLog,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_read', 'created_at', 'related_transaction')
    list_select_related = ('user', 'related_transaction')
    list_filter = ('is_read', 'created_at', 'user')
    search_fields = ('title', 'message', 'user__username')
    ordering = ('-created_at',)

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('to_email', 'subject', 'user', 'sent_at', 'status')
    list_select_related = ('user',)
    list_filter = ('sent_at', 'status')
    search_fields = ('to_email', 'subject', 'body', 'user__username')
    readonly_fields = ('to_email', 'subject', 'body', 'html_body', 'sent_at', 'status', 'error_message', 'user')
    ordering = ('-sent_at',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'limit', 'user')
    list_select_related = ('user',)
    list_filter = ('user',)
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'category', 'amount', 'user')
    list_select_related = ('user',)
    list_filter = ('date', 'user', 'category')
    search_fields = ('description', 'category', 'user__username')
    ordering = ('-date',)

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('date', 'source', 'amount', 'user')
    list_select_related = ('user',)
    list_filter = ('date', 'user', 'source')
    search_fields = ('source', 'description', 'user__username')
    ordering = ('-date',)

@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'transaction_type', 'amount', 'frequency', 'next_due_date', 'user', 'is_active')
    list_select_related = ('user',)
    list_filter = ('transaction_type', 'frequency', 'is_active', 'user')
    search_fields = ('description', 'user__username')

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'balance', 'currency', 'user')
    list_select_related = ('user',)
    list_filter = ('account_type', 'currency', 'user')
    search_fields = ('name', 'user__username')

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('date', 'from_account', 'to_account', 'amount', 'user')
    list_select_related = ('user', 'from_account', 'to_account')
    list_filter = ('date', 'from_account', 'to_account', 'user')
    search_fields = ('description', 'user__username')
    ordering = ('-date',)

from .models import PaymentHistory, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tier', 'subscription_end_date', 'is_lifetime', 'is_pro', 'email_verified')
    list_select_related = ('user',)
    list_filter = ('tier', 'is_lifetime')
    search_fields = ('user__username', 'user__email')

    def email_verified(self, obj):
        from allauth.account.models import EmailAddress
        try:
            email_address = EmailAddress.objects.get(user=obj.user, primary=True)
            return email_address.verified
        except EmailAddress.DoesNotExist:
            return False
    email_verified.boolean = True
    
@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'tier', 'status', 'created_at')
    list_filter = ('status', 'tier')
    search_fields = ('user__username', 'order_id', 'payment_id')

from .models import SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'duration', 'price', 'is_active')
    list_editable = ('price', 'is_active')
    list_filter = ('tier', 'duration')
    ordering = ('tier', 'price')

# Re-register User Admin to include Email Verification inline
from allauth.account.models import EmailAddress
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User


class EmailAddressInline(admin.StackedInline):
    model = EmailAddress
    extra = 0

class UserAdmin(BaseUserAdmin):
    inlines = (EmailAddressInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login', 'date_joined')

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
