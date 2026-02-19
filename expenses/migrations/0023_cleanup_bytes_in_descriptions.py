from django.db import migrations

def cleanup_bytes(apps, schema_editor):
    Expense = apps.get_model('expenses', 'Expense')
    Income = apps.get_model('expenses', 'Income')
    RecurringTransaction = apps.get_model('expenses', 'RecurringTransaction')

    def clean_field(obj, field_name):
        val = getattr(obj, field_name)
        if isinstance(val, bytes):
            # Best effort decoding
            decoded_val = val.decode('utf-8', errors='replace')
            setattr(obj, field_name, decoded_val)
            return True
        return False

    # Clean Expense
    for obj in Expense.objects.all():
        updated = False
        if clean_field(obj, 'description'):
            updated = True
        if clean_field(obj, 'category'):
            updated = True
        if updated:
            obj.save()

    # Clean Income
    for obj in Income.objects.all():
        updated = False
        if clean_field(obj, 'description'):
            updated = True
        if clean_field(obj, 'source'):
            updated = True
        if updated:
            obj.save()

    # Clean RecurringTransaction
    for obj in RecurringTransaction.objects.all():
        updated = False
        if clean_field(obj, 'description'):
            updated = True
        if clean_field(obj, 'category'):
            updated = True
        if clean_field(obj, 'source'):
            updated = True
        if updated:
            obj.save()

def reverse_cleanup(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0022_alter_expense_description_alter_income_description_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_bytes, reverse_cleanup),
    ]
