from django.contrib import admin
from .models import Expense, Category, Income, RecurringTransaction, Notification, Tag, SIPInvestment, FilterPreset

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_read', 'created_at', 'related_transaction')
    list_select_related = ('user', 'related_transaction')
    list_filter = ('is_read', 'created_at', 'user')
    search_fields = ('title', 'message', 'user__username')
    ordering = ('-created_at',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'limit', 'user')
    list_select_related = ('user',)
    list_filter = ('user',)
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'category', 'amount', 'user', 'get_tags')
    list_select_related = ('user',)
    list_filter = ('category', 'date', 'user', 'tags')
    search_fields = ('description', 'category')
    ordering = ('-date',)
    filter_horizontal = ('tags',)

    def get_tags(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])
    get_tags.short_description = 'Tags'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'user', 'get_usage_count')
    list_filter = ('color', 'user')
    search_fields = ('name',)

    def get_usage_count(self, obj):
        return obj.expense_set.count()
    get_usage_count.short_description = 'Used In'


@admin.register(SIPInvestment)
class SIPInvestmentAdmin(admin.ModelAdmin):
    list_display = ('fund_name', 'user', 'amount_per_installment', 'frequency', 'sip_day', 'is_active', 'get_total_paid', 'get_installments')
    list_filter = ('frequency', 'is_active', 'user')
    search_fields = ('fund_name',)
    ordering = ('-start_date',)

    def get_total_paid(self, obj):
        return f"₹{obj.total_paid:,.2f}"
    get_total_paid.short_description = 'Total Paid'

    def get_installments(self, obj):
        return obj.installments_count
    get_installments.short_description = 'Installments'


@admin.register(FilterPreset)
class FilterPresetAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name',)

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('date', 'source', 'amount', 'user')
    list_select_related = ('user',)
    list_filter = ('source', 'date', 'user')
    search_fields = ('description', 'source')
    ordering = ('-date',)

@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'transaction_type', 'amount', 'frequency', 'next_due_date', 'user', 'is_active')
    list_select_related = ('user',)
    list_filter = ('transaction_type', 'frequency', 'is_active', 'user')
    search_fields = ('description',)

from .models import UserProfile, PaymentHistory

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
    list_display = ('name', 'tier', 'price', 'is_active')
    list_editable = ('price', 'is_active')
    ordering = ('price',)

# Re-register User Admin to include Email Verification inline
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from allauth.account.models import EmailAddress

class EmailAddressInline(admin.StackedInline):
    model = EmailAddress
    extra = 0

class UserAdmin(BaseUserAdmin):
    inlines = (EmailAddressInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login', 'date_joined')

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
