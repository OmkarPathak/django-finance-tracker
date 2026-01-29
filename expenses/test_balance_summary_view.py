"""
Tests for BalanceSummaryView.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from datetime import date
from .models import Expense, SharedExpense, SharedExpenseParticipant, Share, Friend


class BalanceSummaryViewTests(TestCase):
    """Test cases for BalanceSummaryView."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.url = reverse('balance-summary')
    
    def create_shared_expense_with_participants(self, expense, participant_data, payer_name):
        """
        Helper method to create a shared expense with participants.
        
        Args:
            expense: The base Expense object
            participant_data: List of dicts with 'name' and 'is_user' keys
            payer_name: Name of the participant who is the payer
        
        Returns:
            tuple: (shared_expense, dict of participants by name)
        """
        # Create SharedExpense
        shared_expense = SharedExpense.objects.create(expense=expense)
        
        # Create all participants
        participants = {}
        for data in participant_data:
            name = data['name']
            is_user = data.get('is_user', False)
            is_payer = (name == payer_name)
            
            friend = None
            if not is_user:
                 friend, _ = Friend.objects.get_or_create(name=name)
            
            participant = SharedExpenseParticipant.objects.create(
                shared_expense=shared_expense,
                friend=friend,
                is_user=is_user,
                is_payer=is_payer
            )
            participants[name] = participant
        
        return shared_expense, participants
    
    def test_view_requires_login(self):
        """Test that the view requires authentication."""
        self.client.logout()
        response = self.client.get(self.url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_view_renders_successfully(self):
        """Test that the view renders successfully for authenticated user."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'expenses/balance_summary.html')
    
    def test_view_with_no_shared_expenses(self):
        """Test view displays empty state when no shared expenses exist."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Shared Expenses Yet')
        self.assertEqual(len(response.context['people_owe_user']), 0)
        self.assertEqual(len(response.context['user_owes_people']), 0)
    
    def test_view_displays_positive_balances(self):
        """Test view displays people who owe the user."""
        # Create expense where user is payer
        expense = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 15),
            amount=Decimal('300.00'),
            description='Dinner',
            category='Food'
        )
        
        shared_expense, participants = self.create_shared_expense_with_participants(
            expense,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Alice', 'is_user': False}
            ],
            payer_name='testuser'
        )
        
        Share.objects.create(
            shared_expense=shared_expense,
            participant=participants['testuser'],
            amount=Decimal('100.00')
        )
        Share.objects.create(
            shared_expense=shared_expense,
            participant=participants['Alice'],
            amount=Decimal('200.00')
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['people_owe_user']), 1)
        self.assertEqual(response.context['people_owe_user'][0]['name'], 'Alice')
        self.assertEqual(response.context['people_owe_user'][0]['net'], Decimal('200.00'))
        self.assertContains(response, 'Alice')
        self.assertContains(response, 'People Owe You')
    
    def test_view_displays_negative_balances(self):
        """Test view displays people the user owes."""
        # Create expense where Alice is payer
        expense = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 15),
            amount=Decimal('200.00'),
            description='Lunch',
            category='Food'
        )
        
        shared_expense, participants = self.create_shared_expense_with_participants(
            expense,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Alice', 'is_user': False}
            ],
            payer_name='Alice'
        )
        
        Share.objects.create(
            shared_expense=shared_expense,
            participant=participants['testuser'],
            amount=Decimal('100.00')
        )
        Share.objects.create(
            shared_expense=shared_expense,
            participant=participants['Alice'],
            amount=Decimal('100.00')
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['user_owes_people']), 1)
        self.assertEqual(response.context['user_owes_people'][0]['name'], 'Alice')
        self.assertEqual(response.context['user_owes_people'][0]['net'], Decimal('-100.00'))
        self.assertContains(response, 'Alice')
        self.assertContains(response, 'You Owe People')
    
    def test_view_with_date_filter(self):
        """Test view filters balances by date range."""
        # Create expense in January
        expense1 = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 15),
            amount=Decimal('100.00'),
            description='January expense',
            category='Food'
        )
        shared_expense1, participants1 = self.create_shared_expense_with_participants(
            expense1,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Alice', 'is_user': False}
            ],
            payer_name='testuser'
        )
        Share.objects.create(
            shared_expense=shared_expense1,
            participant=participants1['testuser'],
            amount=Decimal('50.00')
        )
        Share.objects.create(
            shared_expense=shared_expense1,
            participant=participants1['Alice'],
            amount=Decimal('50.00')
        )
        
        # Create expense in February
        expense2 = Expense.objects.create(
            user=self.user,
            date=date(2024, 2, 15),
            amount=Decimal('200.00'),
            description='February expense',
            category='Food'
        )
        shared_expense2, participants2 = self.create_shared_expense_with_participants(
            expense2,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Alice', 'is_user': False}
            ],
            payer_name='testuser'
        )
        Share.objects.create(
            shared_expense=shared_expense2,
            participant=participants2['testuser'],
            amount=Decimal('100.00')
        )
        Share.objects.create(
            shared_expense=shared_expense2,
            participant=participants2['Alice'],
            amount=Decimal('100.00')
        )
        
        # Filter for January only
        response = self.client.get(self.url, {'year': '2024', 'month': '1'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['filter_applied'])
        self.assertEqual(response.context['selected_month'], 1)
        self.assertEqual(response.context['selected_year'], 2024)
        
        # Should only show January balance
        self.assertEqual(len(response.context['people_owe_user']), 1)
        self.assertEqual(response.context['people_owe_user'][0]['net'], Decimal('50.00'))
    
    def test_view_calculates_totals(self):
        """Test view calculates total amounts correctly."""
        # Create multiple expenses with different people
        expense1 = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 15),
            amount=Decimal('300.00'),
            description='Expense 1',
            category='Food'
        )
        shared_expense1, participants1 = self.create_shared_expense_with_participants(
            expense1,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Alice', 'is_user': False}
            ],
            payer_name='testuser'
        )
        Share.objects.create(
            shared_expense=shared_expense1,
            participant=participants1['testuser'],
            amount=Decimal('100.00')
        )
        Share.objects.create(
            shared_expense=shared_expense1,
            participant=participants1['Alice'],
            amount=Decimal('200.00')
        )
        
        expense2 = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 20),
            amount=Decimal('150.00'),
            description='Expense 2',
            category='Food'
        )
        shared_expense2, participants2 = self.create_shared_expense_with_participants(
            expense2,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Bob', 'is_user': False}
            ],
            payer_name='Bob'
        )
        Share.objects.create(
            shared_expense=shared_expense2,
            participant=participants2['testuser'],
            amount=Decimal('75.00')
        )
        Share.objects.create(
            shared_expense=shared_expense2,
            participant=participants2['Bob'],
            amount=Decimal('75.00')
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        # Alice owes 200, user owes Bob 75
        self.assertEqual(response.context['total_owed_to_user'], Decimal('200.00'))
        self.assertEqual(response.context['total_user_owes'], Decimal('75.00'))
        self.assertEqual(response.context['overall_net'], Decimal('125.00'))
