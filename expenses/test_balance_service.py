"""
Tests for BalanceCalculationService.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from .models import Expense, SharedExpense, Participant, Share
from .services import BalanceCalculationService


class BalanceCalculationServiceTests(TestCase):
    """Test cases for BalanceCalculationService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='password')
    
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
        from django.db import connection
        
        # Temporarily defer constraints to handle circular dependency
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS ALL DEFERRED')
        
        # Create SharedExpense with a placeholder payer_id
        shared_expense = SharedExpense(expense=expense, payer_id=999999)
        shared_expense.save()
        
        # Create all participants
        participants = {}
        for data in participant_data:
            participant = Participant.objects.create(
                shared_expense=shared_expense,
                name=data['name'],
                is_user=data.get('is_user', False)
            )
            participants[data['name']] = participant
        
        # Set the actual payer
        shared_expense.payer = participants[payer_name]
        shared_expense.save()
        
        return shared_expense, participants
        
    
    def test_calculate_balances_user_is_payer(self):
        """
        Test balance calculation when user is the payer.
        Requirements: 6.1, 6.3
        """
        # Create a shared expense where user is payer
        expense = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 15),
            amount=Decimal('300.00'),
            description='Dinner',
            category='Food'
        )
        
        # Create shared expense with participants
        shared_expense, participants = self.create_shared_expense_with_participants(
            expense,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Alice', 'is_user': False},
                {'name': 'Bob', 'is_user': False}
            ],
            payer_name='testuser'
        )
        
        # Create shares (equal split: 100 each)
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
        Share.objects.create(
            shared_expense=shared_expense,
            participant=participants['Bob'],
            amount=Decimal('100.00')
        )
        
        # Calculate balances
        balances = BalanceCalculationService.calculate_balances(self.user)
        
        # User lent 100 to Alice and 100 to Bob (excluding own share)
        self.assertEqual(balances['Alice']['lent'], Decimal('100.00'))
        self.assertEqual(balances['Alice']['borrowed'], Decimal('0.00'))
        self.assertEqual(balances['Alice']['net'], Decimal('100.00'))
        
        self.assertEqual(balances['Bob']['lent'], Decimal('100.00'))
        self.assertEqual(balances['Bob']['borrowed'], Decimal('0.00'))
        self.assertEqual(balances['Bob']['net'], Decimal('100.00'))
    
    def test_calculate_balances_user_is_not_payer(self):
        """
        Test balance calculation when user is not the payer.
        Requirements: 6.2
        """
        # Create a shared expense where Alice is payer
        expense = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 20),
            amount=Decimal('200.00'),
            description='Lunch',
            category='Food'
        )
        
        # Create shared expense with participants
        shared_expense, participants = self.create_shared_expense_with_participants(
            expense,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Alice', 'is_user': False}
            ],
            payer_name='Alice'
        )
        
        # Create shares (equal split: 100 each)
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
        
        # Calculate balances
        balances = BalanceCalculationService.calculate_balances(self.user)
        
        # User borrowed 100 from Alice
        self.assertEqual(balances['Alice']['lent'], Decimal('0.00'))
        self.assertEqual(balances['Alice']['borrowed'], Decimal('100.00'))
        self.assertEqual(balances['Alice']['net'], Decimal('-100.00'))
    
    def test_calculate_balances_net_calculation(self):
        """
        Test net balance calculation with multiple expenses.
        Requirements: 6.5
        """
        # Expense 1: User pays 300, split with Alice (user: 100, Alice: 200)
        expense1 = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 10),
            amount=Decimal('300.00'),
            description='Dinner',
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
        
        # Expense 2: Alice pays 150, split equally
        expense2 = Expense.objects.create(
            user=self.user,
            date=date(2024, 1, 15),
            amount=Decimal('150.00'),
            description='Coffee',
            category='Food'
        )
        shared_expense2, participants2 = self.create_shared_expense_with_participants(
            expense2,
            [
                {'name': 'testuser', 'is_user': True},
                {'name': 'Alice', 'is_user': False}
            ],
            payer_name='Alice'
        )
        
        Share.objects.create(
            shared_expense=shared_expense2,
            participant=participants2['testuser'],
            amount=Decimal('75.00')
        )
        Share.objects.create(
            shared_expense=shared_expense2,
            participant=participants2['Alice'],
            amount=Decimal('75.00')
        )
        
        # Calculate balances
        balances = BalanceCalculationService.calculate_balances(self.user)
        
        # User lent 200 to Alice, borrowed 75 from Alice
        # Net: 200 - 75 = 125
        self.assertEqual(balances['Alice']['lent'], Decimal('200.00'))
        self.assertEqual(balances['Alice']['borrowed'], Decimal('75.00'))
        self.assertEqual(balances['Alice']['net'], Decimal('125.00'))
    
    def test_calculate_balances_with_date_range(self):
        """
        Test balance calculation with date range filtering.
        """
        # Expense in January
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
        
        # Expense in February
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
        
        # Calculate balances for January only
        balances_jan = BalanceCalculationService.calculate_balances(
            self.user,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        # Should only include January expense
        self.assertEqual(balances_jan['Alice']['lent'], Decimal('50.00'))
        
        # Calculate balances for all time
        balances_all = BalanceCalculationService.calculate_balances(self.user)
        
        # Should include both expenses
        self.assertEqual(balances_all['Alice']['lent'], Decimal('150.00'))
