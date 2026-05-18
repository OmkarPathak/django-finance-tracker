from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0052_alter_journalline_ledger_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='recurringtransaction',
            name='loan',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recurring_schedules', to='expenses.loan', verbose_name='Loan'),
        ),
        migrations.AlterField(
            model_name='recurringtransaction',
            name='transaction_type',
            field=models.CharField(choices=[('EXPENSE', 'Expense'), ('INCOME', 'Income'), ('TRANSFER', 'Transfer'), ('LOAN', 'Loan Repayment')], max_length=10, verbose_name='Transaction Type'),
        ),
    ]
