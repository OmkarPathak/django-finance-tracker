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

    def test_income_list_combined_filter(self):
        # Salary in Jan
        response = self.client.get(reverse('income-list'), {'source': 'Salary', 'date_to': '2023-01-31'})
        self.assertEqual(len(response.context['incomes']), 1)
        self.assertEqual(response.context['incomes'][0].source, 'Salary Jan')
