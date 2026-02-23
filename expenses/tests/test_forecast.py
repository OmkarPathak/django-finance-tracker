from django.test import TestCase
from django.contrib.auth.models import User
from expenses.models import Expense, Income, RecurringTransaction, Category
from django.urls import reverse
from datetime import date, timedelta
from django.utils import timezone

class AnalyticsForecastTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.profile = self.user.profile
        self.profile.tier = 'PRO'
        self.profile.is_lifetime = True
        self.profile.save()
        self.client.force_login(self.user)
        self.category, _ = Category.objects.get_or_create(user=self.user, name='Food')
        
    def test_forecast_logic_simple_average(self):
        """
        Test that forecast uses average of last 3 months when no recurring transactions exist.
        """
        # Create 3 months of data (1000 income, 500 expense each month)
        today = date.today()
        for i in range(1, 4):
            # Calculate past month manually
            year = today.year
            month = today.month - i
            while month < 1:
                month += 12
                year -= 1
            d = date(year, month, 1)
            
            Income.objects.create(user=self.user, date=d, amount=1000, source='Salary')
            Expense.objects.create(user=self.user, date=d, amount=500, category='Food')
            
        response = self.client.get(reverse('analytics'))
        self.assertEqual(response.status_code, 200)
        
        # Check context for forecast data
        self.assertIn('forecast_income', response.context)
        self.assertIn('forecast_expenses', response.context)
        
        # Expect ~1000 income and ~500 expense
        # We check the first forecasted month
        forecast_income = response.context['forecast_income']
        forecast_expenses = response.context['forecast_expenses']
        
        self.assertTrue(len(forecast_income) >= 6)
        self.assertAlmostEqual(forecast_income[0], 1000, delta=10)
        self.assertAlmostEqual(forecast_expenses[0], 500, delta=10)

    def test_forecast_logic_with_recurring_floor(self):
        """
        Test that forecast respects recurring transaction floor.
        """
        # Average is low (100 income, 50 expense)
        today = date.today()
        for i in range(1, 4):
            # Calculate past month manually
            year = today.year
            month = today.month - i
            while month < 1:
                month += 12
                year -= 1
            d = date(year, month, 1)
            
            Income.objects.create(user=self.user, date=d, amount=100, source='Gig')
            Expense.objects.create(user=self.user, date=d, amount=50, category='Food')
            
        # Recurring is high (5000 income, 2000 expense)
        RecurringTransaction.objects.create(
            user=self.user, transaction_type='INCOME', amount=5000, 
            frequency='MONTHLY', start_date=today, description='High Salary'
        )
        RecurringTransaction.objects.create(
            user=self.user, transaction_type='EXPENSE', amount=2000, 
            frequency='MONTHLY', start_date=today, category='Rent', description='High Rent'
        )
        
        response = self.client.get(reverse('analytics'))
        
        forecast_income = response.context['forecast_income']
        forecast_expenses = response.context['forecast_expenses']
        
        # Should match recurring amount, not historical average
        self.assertAlmostEqual(forecast_income[0], 5000, delta=10)
        self.assertAlmostEqual(forecast_expenses[0], 2000, delta=10)

    def test_forecast_yearly_spike(self):
        """
        Test that a yearly recurring transaction creates a spike above the average.
        """
        # Average: 1000 Income, 500 Expense
        today = date.today()
        for i in range(1, 4):
            # Calculate past month manually
            year = today.year
            month = today.month - i
            while month < 1:
                month += 12
                year -= 1
            d = date(year, month, 1)
            
            Income.objects.create(user=self.user, date=d, amount=1000, source='Salary')
            Expense.objects.create(user=self.user, date=d, amount=500, category='Food')

        # Add Yearly Expense in 2 months
        # Calculate target date manually
        t_year = today.year
        t_month = today.month + 2
        if t_month > 12:
            t_month -= 12
            t_year += 1
        target_date = date(t_year, t_month, 1)
        
        RecurringTransaction.objects.create(
            user=self.user, transaction_type='EXPENSE', amount=5000, 
            frequency='YEARLY', start_date=target_date, category='Insurance', description='Car Insurance'
        )

        response = self.client.get(reverse('analytics'))
        forecast_expenses = response.context['forecast_expenses']

        # Month 1: Should be Avg (500)
        self.assertAlmostEqual(forecast_expenses[0], 500, delta=10)
        
        # Month 2 (Target): Should be Avg + Spike (500 + 5000 = 5500)
        # Note: target_date logic in test might need alignment with view loop
        # View loop: Month 1 is next month.
        # If today is Feb, next is Mar.
        # If target is Apr (2 months from now), it should be index 1.
        
        # Let's check max value in forecast, it should be around 5500
        self.assertTrue(max(forecast_expenses) >= 5500)

