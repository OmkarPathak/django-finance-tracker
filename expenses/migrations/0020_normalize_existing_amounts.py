from django.db import migrations
from decimal import Decimal

def normalize_historical_data(apps, schema_editor):
    Expense = apps.get_model('expenses', 'Expense')
    Income = apps.get_model('expenses', 'Income')
    RecurringTransaction = apps.get_model('expenses', 'RecurringTransaction')

    # Normalize Expenses
    for expense in Expense.objects.all():
        if expense.base_amount == 0:
            expense.base_amount = expense.amount
            expense.exchange_rate = Decimal('1.0')
            expense.save()

    # Normalize Incomes
    for income in Income.objects.all():
        if income.base_amount == 0:
            income.base_amount = income.amount
            income.exchange_rate = Decimal('1.0')
            income.save()

    # Normalize RecurringTransactions
    for rt in RecurringTransaction.objects.all():
        if rt.base_amount == 0:
            rt.base_amount = rt.amount
            rt.exchange_rate = Decimal('1.0')
            rt.save()

class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0019_remove_expense_unique_expense_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_historical_data),
    ]
