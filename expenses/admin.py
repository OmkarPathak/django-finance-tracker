from django.contrib import admin
from .models import Expense

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'category', 'amount', 'user')
    list_filter = ('category', 'date', 'user')
    search_fields = ('description', 'category')
    ordering = ('-date',)
