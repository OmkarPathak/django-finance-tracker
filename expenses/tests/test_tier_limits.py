from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from expenses.models import Account, Expense, UserProfile

class TierLimitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="freetester", password="password")
        # Ensure profile exists (signals might be skipped in some test setups)
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.tier = "FREE"
        self.profile.has_seen_tutorial = True
        self.profile.save()
        
        self.client = Client()
        self.client.login(username="freetester", password="password")

    def test_account_limit_enforced(self):
        """Free user should not be able to create more than 3 accounts."""
        # Create 3 accounts
        for i in range(3):
            Account.objects.create(user=self.user, name=f"Acc {i}", balance=100)
        
        self.assertEqual(self.user.accounts.count(), 3)
        
        # Try to create 4th account via view
        response = self.client.post(reverse('account-create'), {
            'name': '4th Account',
            'account_type': 'BANK',
            'balance': '100',
            'currency': '₹'
        })
        
        # Should redirect to pricing or show error message
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)
        self.assertEqual(self.user.accounts.count(), 3)

    def test_expense_monthly_limit_enforced(self):
        """Free user should not be able to create more than 30 expenses in a month."""
        # Create 30 expenses for current month
        today = date.today()
        for i in range(30):
            Expense.objects.create(
                user=self.user,
                date=today,
                amount=Decimal("10.00"),
                description=f"Expense {i}",
                category="Food"
            )
        
        # Try to create 31st expense via view
        # ExpenseCreateView uses a formset
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-date': today.strftime('%Y-%m-%d'),
            'form-0-amount': '20.00',
            'form-0-description': '31st Expense',
            'form-0-category': 'Food',
            'form-0-currency': '₹',
            'form-0-payment_method': 'Cash'
        }
        response = self.client.post(reverse('expense-create'), data)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)
        
        month_count = Expense.objects.filter(user=self.user, date__year=today.year, date__month=today.month).count()
        self.assertEqual(month_count, 30)

    def test_net_worth_locked_for_free_user(self):
        """Dashboard should indicate net worth is locked for free users."""
        response = self.client.get(reverse('home'))
        self.assertTrue(response.context['is_net_worth_locked'])
        self.assertContains(response, "Track Your Net Worth")
        self.assertContains(response, "nw-locked-overlay")

    def test_net_worth_unlocked_for_plus_user(self):
        """Dashboard should NOT indicate net worth is locked for plus users."""
        self.profile.tier = "PLUS"
        self.profile.subscription_end_date = timezone.now().date() + timedelta(days=30)
        self.profile.save()
        
        response = self.client.get(reverse('home'))
        self.assertFalse(response.context['is_net_worth_locked'])
        # Check that the overlay text is NOT present (the class name is always in the style tag)
        self.assertNotContains(response, "Unlock live net worth tracking")
