import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from expenses.models import Category, RecurringTransaction, UserProfile
from finance_tracker.plans import PLAN_DETAILS, get_limit


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
        """Free tier should limit to the configured categories."""
        self.setup_tier('FREE')
        limit = PLAN_DETAILS['FREE']['limits']['budget_categories']
        if limit == -1: return # Skip if unlimited
        for i in range(limit):
            Category.objects.create(user=self.user, name=f'Cat {i}')
        
        # Adding one more category should fail (AJAX)
        response = self.client.post(
            reverse('category-create-ajax'),
            data=json.dumps({'name': f'Cat {limit+1}'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(json.loads(response.content)['success'])

    def test_plus_tier_category_limit(self):
        """Plus tier should limit to the configured categories."""
        self.setup_tier('PLUS')
        limit = PLAN_DETAILS['PLUS']['limits']['budget_categories']
        if limit == -1: return # Skip if unlimited
        for i in range(limit):
            Category.objects.create(user=self.user, name=f'Cat {i}')
        
        # Adding one more category should fail
        response = self.client.post(reverse('category-create'), {'name': f'Cat {limit+1}'})
        # Should redirect back with error message (or to pricing page depending on view logic)
        self.assertEqual(response.status_code, 302)
        
        # Verify extra was NOT created
        self.assertEqual(Category.objects.filter(user=self.user).count(), limit)

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
        """Free tier should respect recurring transaction limits."""
        self.setup_tier('FREE')
        limit = PLAN_DETAILS['FREE']['limits']['recurring_transactions']
        if limit == -1: return
        Category.objects.create(user=self.user, name='Food')
        
        # Fill up to limit
        for i in range(limit):
            RecurringTransaction.objects.create(
                user=self.user, transaction_type='EXPENSE', amount=100, 
                description=f'RT {i}', frequency='MONTHLY', start_date=date.today(), category='Food'
            )
            
        # Try one more
        response = self.client.post(reverse('recurring-create'), {
            'transaction_type': 'EXPENSE', 'amount': 100, 'description': 'Limit Check',
            'frequency': 'MONTHLY', 'start_date': date.today(), 'category': 'Food',
            'currency': '₹', 'payment_method': 'Cash'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('pricing', response.url)
        self.assertEqual(RecurringTransaction.objects.filter(user=self.user).count(), limit)

    def test_plus_tier_recurring_limit(self):
        """Plus tier should respect the configured recurring transaction limit."""
        self.setup_tier('PLUS')
        limit = PLAN_DETAILS['PLUS']['limits']['recurring_transactions']
        if limit == -1: return
        Category.objects.create(user=self.user, name='Food')
        for i in range(limit):
            RecurringTransaction.objects.create(
                user=self.user,
                transaction_type='EXPENSE',
                amount=100,
                description=f'RT {i}',
                frequency='MONTHLY',
                start_date=date.today(),
                category='Food'
            )
        
        # Try one more
        response = self.client.post(reverse('recurring-create'), {
            'transaction_type': 'EXPENSE',
            'amount': 100,
            'description': 'Limit Check Extra',
            'frequency': 'MONTHLY',
            'start_date': date.today(),
            'category': 'Food',
            'currency': '₹',
            'payment_method': 'Cash'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('pricing', response.url)
        self.assertEqual(RecurringTransaction.objects.filter(user=self.user).count(), limit)

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

        from expenses.models import Notification, RecurringTransaction
        
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
            new_month = d.month - 1
            new_year = d.year
            if new_month == 0:
                new_month = 12
                new_year -= 1
            
            # Handle day out of range (e.g. March 31 -> Feb 28/29)
            new_day = d.day
            while True:
                try:
                    return date(new_year, new_month, new_day)
                except ValueError:
                    new_day -= 1
        
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
        """Only users with ai_insights access can access AI category prediction."""
        for tier in ['FREE', 'PLUS', 'PRO']:
            self.setup_tier(tier)
            has_access = PLAN_DETAILS[tier]['limits']['ai_insights']
            
            with patch('expenses.views.predict_category_ai') as mock_ai:
                mock_ai.return_value = 'Food'
                response = self.client.get(reverse('predict-category'), {'description': 'Milk'})
                
                if has_access:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['category'], 'Food')
                else:
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(response.json()['error'], 'AI Insights is a paid feature.')
