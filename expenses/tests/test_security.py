from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from expenses.models import (
    Expense,
    Income,
)


class DataSegregationTest(TestCase):
    def setUp(self):
        # User A
        self.user_a = User.objects.create_user(username='usera', password='password')
        self.user_a.profile.has_seen_tutorial = True
        self.user_a.profile.save()
        self.client_a = Client()
        self.client_a.login(username='usera', password='password')
        
        # User B
        self.user_b = User.objects.create_user(username='userb', password='password')
        self.user_b.profile.has_seen_tutorial = True
        self.user_b.profile.save()
        self.client_b = Client()
        self.client_b.login(username='userb', password='password')

        # Create data for User A
        self.expense_a = Expense.objects.create(user=self.user_a, date=date.today(), amount=100, description='User A Expense', category='Food')
        self.income_a = Income.objects.create(user=self.user_a, date=date.today(), amount=1000, source='Salary A')
        
        # Create data for User B
        self.expense_b = Expense.objects.create(user=self.user_b, date=date.today(), amount=200, description='User B Expense', category='Food')
        
    def test_dashboard_isolation(self):
        """User B should not see User A's data on dashboard"""
        response = self.client_b.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        
        activity = response.context['recent_activity']
        
        # Check Expenses
        self.assertTrue(any(getattr(e, 'description', '') == 'User B Expense' for e in activity))
        self.assertFalse(any(getattr(e, 'description', '') == 'User A Expense' for e in activity))
        
        # Check Income (User B has 0 income)
        self.assertEqual(response.context['total_income'], 0)

    def test_expense_list_isolation(self):
        """User B should not see User A's expenses in list view"""
        response = self.client_b.get(reverse('expense-list'))
        expenses = response.context['expenses']
        
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0].description, 'User B Expense')

    def test_update_expense_permission(self):
        """User B should not be able to edit User A's expense"""
        url = reverse('expense-edit', kwargs={'pk': self.expense_a.pk})
        
        # Attempt to access edit page
        response = self.client_b.get(url)
        # Should return 404 because get_queryset filters by user, or 403.
        # Standard ListView/UpdateView with login_required usually does get_object. 
        # If queryset is filtered by user, it returns 404.
        self.assertEqual(response.status_code, 404)
        
        # Attempt to POST update
        response = self.client_b.post(url, {
            'date': date.today(),
            'amount': 5000,
            'description': 'HACKED',
            'category': 'Food',
            'payment_method': 'Cash'
        })
        self.assertEqual(response.status_code, 404)
        
        # Verify object was not changed
        self.expense_a.refresh_from_db()
        self.assertEqual(self.expense_a.amount, 100)
        self.assertEqual(self.expense_a.description, 'User A Expense')

    def test_delete_expense_permission(self):
        """User B should not be able to delete User A's expense"""
        url = reverse('expense-delete', kwargs={'pk': self.expense_a.pk})
        
        response = self.client_b.post(url)
        self.assertEqual(response.status_code, 404)
        
        # Verify object still exists
        self.assertTrue(Expense.objects.filter(pk=self.expense_a.pk).exists())
