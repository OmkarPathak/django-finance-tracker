from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from expenses.models import UserProfile, Category, RecurringTransaction
from datetime import date
from unittest.mock import patch
import json

class SubscriptionTierTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='subuser', password='password', email='sub@example.com')
        # Clear categories created by signals
        Category.objects.filter(user=self.user).delete()
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.client = Client()
        self.client.login(username='subuser', password='password')

    def setup_tier(self, tier):
        self.profile.tier = tier
        if tier != 'FREE':
            self.profile.is_lifetime = True
        else:
            self.profile.is_lifetime = False
        self.profile.save()

    def test_free_tier_category_limit(self):
        """Free tier should limit to 5 categories."""
        self.setup_tier('FREE')
        for i in range(5):
            Category.objects.create(user=self.user, name=f'Cat {i}')
        
        # Adding 6th category should fail (AJAX)
        response = self.client.post(
            reverse('category-create-ajax'),
            data=json.dumps({'name': 'Cat 6'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(json.loads(response.content)['success'])

    def test_plus_tier_category_limit(self):
        """Plus tier should limit to 10 categories."""
        self.setup_tier('PLUS')
        for i in range(10):
            Category.objects.create(user=self.user, name=f'Cat {i}')
        
        # Adding 11th category should fail
        response = self.client.post(reverse('category-create'), {'name': 'Cat 11'})
        # Should redirect back to create with error message
        self.assertEqual(response.status_code, 302)
        
        # Verify 11th was NOT created
        self.assertEqual(Category.objects.filter(user=self.user).count(), 10)

    def test_pro_tier_category_limit(self):
        """Pro tier should have unlimited categories."""
        self.setup_tier('PRO')
        for i in range(12): # More than Plus limit
            Category.objects.create(user=self.user, name=f'Cat {i}')
        
        # Should still be able to add more via AJAX
        response = self.client.post(
            reverse('category-create-ajax'),
            data=json.dumps({'name': 'Cat Extra'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['success'])

    def test_free_tier_recurring_limit(self):
        """Free tier should not allow recurring transactions."""
        self.setup_tier('FREE')
        Category.objects.create(user=self.user, name='Food')
        response = self.client.post(reverse('recurring-create'), {
            'transaction_type': 'EXPENSE',
            'amount': 100,
            'description': 'Test',
            'frequency': 'MONTHLY',
            'start_date': date.today(),
            'category': 'Food',
            'currency': '₹',
            'payment_method': 'Cash'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('pricing', response.url)
        self.assertEqual(RecurringTransaction.objects.filter(user=self.user).count(), 0)

    def test_plus_tier_recurring_limit(self):
        """Plus tier should allow 3 recurring transactions."""
        self.setup_tier('PLUS')
        Category.objects.create(user=self.user, name='Food')
        for i in range(3):
            RecurringTransaction.objects.create(
                user=self.user,
                transaction_type='EXPENSE',
                amount=100,
                description=f'RT {i}',
                frequency='MONTHLY',
                start_date=date.today(),
                category='Food'
            )
        
        # 4th should fail
        response = self.client.post(reverse('recurring-create'), {
            'transaction_type': 'EXPENSE',
            'amount': 100,
            'description': 'RT 4',
            'frequency': 'MONTHLY',
            'start_date': date.today(),
            'category': 'Food',
            'currency': '₹',
            'payment_method': 'Cash'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('pricing', response.url)
        self.assertEqual(RecurringTransaction.objects.filter(user=self.user).count(), 3)

    def test_export_access(self):
        """Only Plus/Pro can export."""
        # Free
        self.setup_tier('FREE')
        response = self.client.get(reverse('export-expenses'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('pricing', response.url)
        
        # Plus
        self.setup_tier('PLUS')
        response = self.client.get(reverse('export-expenses'))
        self.assertEqual(response.status_code, 200) # CSV returned
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_email_reminder_gate(self):
        """Only Plus/Pro receive email reminders."""
        from io import StringIO
        from django.core.management import call_command
        from expenses.models import RecurringTransaction, Notification
        
        rt = RecurringTransaction.objects.create(
            user=self.user,
            transaction_type='EXPENSE',
            amount=100,
            description='Due Soon',
            frequency='MONTHLY',
            start_date=date.today(),
            last_processed_date=None
        )
        # Mock next_due_date to be exactly 3 days from now
        from datetime import timedelta
        target_due = date.today() + timedelta(days=3)
        
        # Adjust start_date and last_processed_date so next_due_date is exactly target_due
        # If monthly, and next is target_due, then last was target_due - 1 month
        def get_last_month(d):
            month = d.month - 1
            year = d.year
            if month == 0:
                month = 12
                year -= 1
            return d.replace(year=year, month=month)
        
        rt.start_date = get_last_month(target_due)
        rt.last_processed_date = get_last_month(target_due)
        rt.save()
        
        # Free Tier
        self.setup_tier('FREE')
        Notification.objects.filter(user=self.user).delete()
        out = StringIO()
        call_command('send_notifications', stdout=out)
        self.assertIn('Skipping email for subuser (Free Tier)', out.getvalue())
        
        # Plus Tier
        self.setup_tier('PLUS')
        Notification.objects.filter(user=self.user).delete()
        out = StringIO()
        call_command('send_notifications', stdout=out)
        self.assertIn('Sent consolidated email to sub@example.com', out.getvalue())

    def test_ai_prediction_gate(self):
        """Only Pro users can access AI category prediction."""
        # Free Tier - Should fail with 403
        self.setup_tier('FREE')
        response = self.client.get(reverse('predict-category'), {'description': 'Milk'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'AI Insights is a Pro feature.')

        # Plus Tier - Should fail with 403
        self.setup_tier('PLUS')
        response = self.client.get(reverse('predict-category'), {'description': 'Milk'})
        self.assertEqual(response.status_code, 403)
        
        # Pro Tier - Should succeed
        self.setup_tier('PRO')
        # We need to mock predictable AI behavior if possible, but the view calls predict_category_ai.
        # Let's mock it to return 'Food'.
        with patch('expenses.views.predict_category_ai') as mock_ai:
            mock_ai.return_value = 'Food'
            response = self.client.get(reverse('predict-category'), {'description': 'Milk'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['category'], 'Food')
