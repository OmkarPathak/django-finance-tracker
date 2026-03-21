from django.db import migrations, models
from decimal import Decimal

def create_default_accounts(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Account = apps.get_model('expenses', 'Account')
    Expense = apps.get_model('expenses', 'Expense')
    Income = apps.get_model('expenses', 'Income')
    RecurringTransaction = apps.get_model('expenses', 'RecurringTransaction')
    
    for user in User.objects.all():
        # Get currency from profile if available
        currency = '₹'
        try:
            if hasattr(user, 'profile'):
                currency = user.profile.currency
        except Exception:
            pass

        # Create a default "Cash" account for each user
        account, created = Account.objects.get_or_create(
            user=user,
            name='Cash',
            defaults={
                'account_type': 'CASH',
                'currency': currency,
                'balance': Decimal('0.00')
            }
        )
        
        # Link existing expenses, incomes and recurring transactions to this account
        Expense.objects.filter(user=user, account__isnull=True).update(account=account)
        Income.objects.filter(user=user, account__isnull=True).update(account=account)
        RecurringTransaction.objects.filter(user=user, account__isnull=True).update(account=account)
        
        # Calculate initial balance based on migrated history
        total_income = Income.objects.filter(account=account).aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        total_expense = Expense.objects.filter(account=account).aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        account.balance = total_income - total_expense
        account.save()

class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0032_account_expense_account_income_account_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_accounts),
    ]
