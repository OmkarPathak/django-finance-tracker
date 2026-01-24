from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Income
from datetime import date

class IncomeListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        
        # Create sample income data
        Income.objects.create(user=self.user, date=date(2023, 1, 1), amount=1000, source='Salary Jan', description='Jan Salary')
        Income.objects.create(user=self.user, date=date(2023, 2, 1), amount=1200, source='Salary Feb', description='Feb Salary')
        Income.objects.create(user=self.user, date=date(2023, 3, 1), amount=1500, source='Freelance', description='Project X')

    def test_income_list_no_filter(self):
        response = self.client.get(reverse('income-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['incomes']), 3)

    def test_income_list_date_filter(self):
        # Filter Feb and Mar
        response = self.client.get(reverse('income-list'), {'date_from': '2023-02-01'})
        self.assertEqual(len(response.context['incomes']), 2)
        
        # Filter Jan only
        response = self.client.get(reverse('income-list'), {'date_to': '2023-01-31'})
        self.assertEqual(len(response.context['incomes']), 1)
        self.assertEqual(response.context['incomes'][0].source, 'Salary Jan')

        # Filter range
        response = self.client.get(reverse('income-list'), {'date_from': '2023-02-01', 'date_to': '2023-02-28'})
        self.assertEqual(len(response.context['incomes']), 1)
        self.assertEqual(response.context['incomes'][0].source, 'Salary Feb')

    def test_income_list_source_filter(self):
        response = self.client.get(reverse('income-list'), {'source': 'Salary'})
        self.assertEqual(len(response.context['incomes']), 2)
        
        response = self.client.get(reverse('income-list'), {'source': 'Freelance'})
        self.assertEqual(len(response.context['incomes']), 1)

        self.assertEqual(len(response.context['incomes']), 1)
        self.assertEqual(response.context['incomes'][0].source, 'Salary Jan')

from .models import Expense
class ExpenseListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='expenseuser', password='password')
        self.client = Client()
        self.client.login(username='expenseuser', password='password')
        
        # Create sample expenses
        Expense.objects.create(user=self.user, date=date(2023, 1, 1), amount=100, description='Low', category='Food', payment_method='Cash')
        Expense.objects.create(user=self.user, date=date(2023, 1, 2), amount=500, description='High', category='Food', payment_method='Cash')
        Expense.objects.create(user=self.user, date=date(2023, 1, 3), amount=300, description='Mid', category='Food', payment_method='Cash')

    def test_sort_amount_asc(self):
        response = self.client.get(reverse('expense-list'), {'sort': 'amount_asc', 'year': '2023'})
        expenses = response.context['expenses']
        self.assertEqual(expenses[0].amount, 100)
        self.assertEqual(expenses[1].amount, 300)
        self.assertEqual(expenses[2].amount, 500)

    def test_sort_amount_desc(self):
        response = self.client.get(reverse('expense-list'), {'sort': 'amount_desc', 'year': '2023'})
        expenses = response.context['expenses']
        self.assertEqual(expenses[0].amount, 500)
        self.assertEqual(expenses[1].amount, 300)
        self.assertEqual(expenses[2].amount, 100)

    def test_sort_default(self):
        # Default is -date (newest first)
        response = self.client.get(reverse('expense-list'), {'year': '2023'})
        expenses = response.context['expenses']
        self.assertEqual(expenses[0].date, date(2023, 1, 3))
        self.assertEqual(expenses[1].date, date(2023, 1, 2))
        self.assertEqual(expenses[2].date, date(2023, 1, 1))
