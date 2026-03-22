from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from expenses.models import Account, Expense, UserProfile, Category, RecurringTransaction

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

    def test_account_limit_enforced_free(self):
        """Free user should not be able to create more than 3 accounts."""
        for i in range(3):
            Account.objects.create(user=self.user, name=f"Acc {i}", balance=100)
        
        self.assertEqual(self.user.accounts.count(), 3)
        
        response = self.client.post(reverse('account-create'), {
            'name': '4th Account', 'account_type': 'BANK', 'balance': '100', 'currency': '₹'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)
        self.assertEqual(self.user.accounts.count(), 3)

    def test_account_limit_enforced_plus(self):
        """Plus user should not be able to create more than 5 accounts."""
        self.profile.tier = "PLUS"
        self.profile.subscription_end_date = timezone.now().date() + timedelta(days=30)
        self.profile.save()

        for i in range(5):
            Account.objects.create(user=self.user, name=f"Acc {i}", balance=100)
        
        self.assertEqual(self.user.accounts.count(), 5)
        
        response = self.client.post(reverse('account-create'), {
            'name': '6th Account', 'account_type': 'BANK', 'balance': '100', 'currency': '₹'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)
        self.assertEqual(self.user.accounts.count(), 5)

    def test_category_limit_enforced_free(self):
        """Free user should not be able to create more than 3 categories."""
        # User starts with 3 default categories (Food, Shopping, Bills) via signals
        self.assertEqual(Category.objects.filter(user=self.user).count(), 3)
        
        response = self.client.post(reverse('category-create'), {'name': '4th Cat'})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)
        self.assertEqual(Category.objects.filter(user=self.user).count(), 3)

    def test_category_limit_enforced_plus(self):
        """Plus user should be capped at 10 categories."""
        self.profile.tier = "PLUS"
        self.profile.subscription_end_date = timezone.now().date() + timedelta(days=30)
        self.profile.save()
        
        # Start with 3 defaults, add 7 more
        for i in range(7):
            Category.objects.create(user=self.user, name=f"Extra {i}")
        
        self.assertEqual(Category.objects.filter(user=self.user).count(), 10)
        
        response = self.client.post(reverse('category-create'), {'name': '11th Cat'})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)
        self.assertEqual(Category.objects.filter(user=self.user).count(), 10)

    def test_recurring_limit_enforced_free(self):
        """Free user should not be able to create any recurring transactions."""
        acc = Account.objects.create(user=self.user, name="Main", balance=1000)
        response = self.client.post(reverse('recurring-create'), {
            'account': acc.id, 'description': 'Monthly Rent', 'amount': '5000',
            'category': 'Rent', 'frequency': 'MONTHLY', 'start_date': date.today()
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)

    def test_recurring_limit_enforced_plus(self):
        """Plus user should be capped at 3 recurring transactions."""
        self.profile.tier = "PLUS"
        self.profile.subscription_end_date = timezone.now().date() + timedelta(days=30)
        self.profile.save()
        acc = Account.objects.create(user=self.user, name="Main", balance=1000)

        for i in range(3):
            RecurringTransaction.objects.create(
                user=self.user, account=acc, description=f"Rec {i}", 
                amount=100, category="Test", frequency="MONTHLY", start_date=date.today()
            )
        
        response = self.client.post(reverse('recurring-create'), {
            'account': acc.id, 'description': '4th Rec', 'amount': '100',
            'category': 'Test', 'frequency': 'MONTHLY', 'start_date': date.today()
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)
        self.assertEqual(RecurringTransaction.objects.filter(user=self.user, is_active=True).count(), 3)

    def test_expense_monthly_limit_enforced(self):
        """Free user should not be able to create more than 30 expenses in a month."""
        today = date.today()
        for i in range(30):
            Expense.objects.create(
                user=self.user, date=today, amount=Decimal("10.00"),
                description=f"Expense {i}", category="Food"
            )
        
        data = {
            'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '0', 'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000', 'form-0-date': today.strftime('%Y-%m-%d'),
            'form-0-amount': '20.00', 'form-0-description': '31st Expense',
            'form-0-category': 'Food', 'form-0-currency': '₹', 'form-0-payment_method': 'Cash'
        }
        response = self.client.post(reverse('expense-create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('pricing'), response.url)
        self.assertEqual(Expense.objects.filter(user=self.user, date__year=today.year, date__month=today.month).count(), 30)

    def test_net_worth_locked_for_free_user(self):
        """Dashboard should indicate net worth is locked for free users."""
        response = self.client.get(reverse('home'))
        self.assertTrue(response.context['is_net_worth_locked'])

    def test_net_worth_unlocked_for_plus_user(self):
        """Dashboard should NOT indicate net worth is locked for plus users."""
        self.profile.tier = "PLUS"
        self.profile.subscription_end_date = timezone.now().date() + timedelta(days=30)
        self.profile.save()
        response = self.client.get(reverse('home'))
        self.assertFalse(response.context['is_net_worth_locked'])
