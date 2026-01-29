from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from expenses.models import UserProfile, Expense, Category
from datetime import date

class BaseFeatureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')

class SettingsViewTest(BaseFeatureTest):
    def test_currency_update(self):
        url = reverse('currency-settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = {'currency': '$'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.currency, '$')

    def test_account_delete(self):
        url = reverse('account-delete')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='testuser').exists())

class FeatureViewTest(BaseFeatureTest):
    def test_calendar_default(self):
        url = reverse('calendar')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_calendar_month(self):
        url = reverse('calendar-month', kwargs={'year': 2025, 'month': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_budget_view(self):
        url = reverse('budget')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_export_expenses(self):
        # Upgrade user to Plus with lifetime access to bypass date check
        self.user.profile.tier = 'PLUS'
        self.user.profile.is_lifetime = True
        self.user.profile.save()
        
        # Create some data
        Category.objects.get_or_create(user=self.user, name='Food')
        Expense.objects.create(user=self.user, date=date.today(), amount=100, category='Food', description='Test')
        
        url = reverse('export-expenses')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('Food', content)
        self.assertIn('100', content)

from expenses.models import RecurringTransaction

class RecurringCRUDTest(BaseFeatureTest):
    def test_create_recurring(self):
        # Upgrade user to Pro for unlimited recurring transactions
        self.user.profile.tier = 'PRO'
        self.user.profile.is_lifetime = True
        self.user.profile.save()

        # Ensure category exists for form choice validation
        Category.objects.get_or_create(user=self.user, name='Entertainment')
        
        url = reverse('recurring-create')
        data = {
            'transaction_type': 'EXPENSE',
            'amount': 500,
            'description': 'Netflix',
            'frequency': 'MONTHLY',
            'start_date': date.today(),
            'category': 'Entertainment',
            'payment_method': 'Cash'
        }
        response = self.client.post(url, data)
        if response.status_code == 200:
             self.fail(f"Form errors: {response.context['form'].errors}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RecurringTransaction.objects.count(), 1)

    def test_update_recurring(self):
        Category.objects.get_or_create(user=self.user, name='Entertainment')
        rt = RecurringTransaction.objects.create(
            user=self.user, transaction_type='EXPENSE', amount=500, description='Netflix',
            frequency='MONTHLY', start_date=date.today(), category='Entertainment'
        )
        url = reverse('recurring-edit', kwargs={'pk': rt.pk})
        data = {
            'transaction_type': 'EXPENSE',
            'amount': 600,
            'description': 'Netflix Premium',
            'frequency': 'MONTHLY',
            'start_date': date.today(),
            'category': 'Entertainment',
            'payment_method': 'Credit Card'
        }
        response = self.client.post(url, data)
        if response.status_code == 200:
             self.fail(f"Form errors: {response.context['form'].errors}")
        self.assertEqual(response.status_code, 302)
        rt.refresh_from_db()
        self.assertEqual(rt.amount, 600)

    def test_delete_recurring(self):
        rt = RecurringTransaction.objects.create(
            user=self.user, transaction_type='EXPENSE', amount=500, description='Netflix',
            frequency='MONTHLY', start_date=date.today()
        )
        url = reverse('recurring-delete', kwargs={'pk': rt.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RecurringTransaction.objects.count(), 0)

from expenses.models import Notification

class NotificationViewTest(BaseFeatureTest):
    def test_notification_list(self):
        Notification.objects.create(user=self.user, title='Title', message='Msg')
        url = reverse('notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check if list is present (paginated_list or object_list)
        self.assertTrue(len(response.context['object_list']) > 0)

    def test_mark_all_read(self):
        Notification.objects.create(user=self.user, title='Title', message='Msg', is_read=False)
        url = reverse('mark-all-read')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Notification.objects.filter(is_read=False).exists())
