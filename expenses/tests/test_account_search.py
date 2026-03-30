from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from expenses.models import Account, Expense, GoalContribution, Income, SavingsGoal, Transfer


class AccountDetailSearchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='searchuser', password='password')
        self.client = Client()
        self.client.login(username='searchuser', password='password')
        
        # Ensure profile exists and tutorial is seen
        profile = self.user.profile
        profile.has_seen_tutorial = True
        profile.currency = '₹'
        profile.save()
        
        self.account = Account.objects.create(user=self.user, name='SearchAccount', balance=Decimal('1000.00'), currency='₹')
        
        # 1. Expense: Apple Music (Subscription) - 100
        Expense.objects.create(
            user=self.user, 
            account=self.account, 
            amount=Decimal('100.00'), 
            date=date.today(), 
            description="Apple Music", 
            category="Subscription"
        )
        
        # 2. Expense: Banana Bread (Food) - 50
        Expense.objects.create(
            user=self.user, 
            account=self.account, 
            amount=Decimal('50.00'), 
            date=date.today(), 
            description="Banana Bread", 
            category="Food"
        )
        
        # 3. Income: Apple Dividend (Dividend) + 500
        Income.objects.create(
            user=self.user, 
            account=self.account, 
            amount=Decimal('500.00'), 
            date=date.today(), 
            description="Apple Dividend", 
            source="Dividend"
        )
        
        # 4. Goal Contribution: MacBook Goal - 200
        self.goal = SavingsGoal.objects.create(user=self.user, name="MacBook", target_amount=Decimal('100000.00'))
        GoalContribution.objects.create(
            goal=self.goal, 
            account=self.account, 
            amount=Decimal('200.00'), 
            date=date.today()
        )
        
        # 5. Transfer OUT: To another account - 150
        self.other_acc = Account.objects.create(user=self.user, name='Other', balance=Decimal('0.00'))
        Transfer.objects.create(
            user=self.user, 
            from_account=self.account, 
            to_account=self.other_acc, 
            amount=Decimal('150.00'), 
            date=date.today(), 
            description="Monthly Transfer"
        )

    def test_view_account_detail_no_search(self):
        """Verify full ledger is returned when no search query is present."""
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['ledger']), 5)
        self.assertEqual(response.context['search_query'], '')

    def test_search_by_description(self):
        """Verify items matching description are returned and others are excluded."""
        # Search "Apple" should match Apple Music and Apple Dividend
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}), {'q': 'Apple'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['ledger']), 2)
        self.assertContains(response, 'Apple Music')
        self.assertContains(response, 'Apple Dividend')
        self.assertNotContains(response, 'Banana Bread')

    def test_search_by_category_and_source(self):
        """Verify filtering by category (Expense) and source (Income)."""
        # Search "Food" should match Banana Bread
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}), {'q': 'Food'})
        self.assertEqual(len(response.context['ledger']), 1)
        self.assertContains(response, 'Banana Bread')
        
        # Search "Dividend" should match Apple Dividend
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}), {'q': 'Dividend'})
        self.assertEqual(len(response.context['ledger']), 1)
        self.assertContains(response, 'Apple Dividend')

    def test_search_by_goal_name(self):
        """Verify filtering works for GoalContribution via goal__name."""
        # Search "MacBook" should match Goal Contribution
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}), {'q': 'MacBook'})
        self.assertEqual(len(response.context['ledger']), 1)
        self.assertContains(response, 'Savings: MacBook')

    def test_filtered_net_total_calculation(self):
        """Verify that filtered_net_total correctly sums items with appropriate signs."""
        # Search "Apple" -> Expense 100, Income 500 => Net +400
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}), {'q': 'Apple'})
        self.assertEqual(response.context['filtered_net_total'], Decimal('400.00'))
        
        # Search "Transfer" -> Transfer OUT 150 => Net -150
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}), {'q': 'Transfer'})
        self.assertEqual(response.context['filtered_net_total'], Decimal('-150.00'))
        
        # Search "MacBook" -> Savings 200 => Net -200
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}), {'q': 'MacBook'})
        self.assertEqual(response.context['filtered_net_total'], Decimal('-200.00'))

    def test_search_no_results(self):
        """Verify handles scenario with no matching results."""
        response = self.client.get(reverse('account-detail', kwargs={'pk': self.account.pk}), {'q': 'NonExistent'})
        self.assertEqual(len(response.context['ledger']), 0)
        self.assertContains(response, 'No results found for')
        self.assertContains(response, 'NonExistent')
