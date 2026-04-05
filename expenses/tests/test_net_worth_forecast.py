from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from expenses.models import Account, Expense, Income

class NetWorthForecastTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.profile = self.user.profile
        self.profile.has_seen_tutorial = True
        self.profile.save()
        self.client.force_login(self.user)
        
        # Create a base account with balance
        self.account = Account.objects.create(
            user=self.user,
            name="Main Bank",
            currency="INR",
            balance=Decimal('100000.00'),
            account_type='SAVINGS'
        )

    def _create_history(self, income_amt, expense_amt, months=3):
        """Helper to create historical data for N months."""
        today = date.today()
        for i in range(1, months + 1):
            # Calculate past month
            year = today.year
            month = today.month - i
            while month < 1:
                month += 12
                year -= 1
            d = date(year, month, 1)
            
            Income.objects.create(user=self.user, date=d, amount=income_amt, source='Salary', base_amount=income_amt)
            Expense.objects.create(user=self.user, date=d, amount=expense_amt, category='Food', base_amount=expense_amt)

    def test_forecast_positive_trend(self):
        """Test forecast with positive savings (Income > Expense)."""
        # 3 months of 10k savings each
        self._create_history(Decimal('50000.00'), Decimal('40000.00'), months=3)
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        
        forecasts = response.context['net_worth_forecasts']
        self.assertEqual(len(forecasts), 3)
        
        # Current NW is 100,000. Avg savings is 10,000.
        # Month 1 projection should be 110,000
        self.assertEqual(forecasts[0]['value'], 110000.0)
        self.assertEqual(forecasts[0]['change'], 10000.0)
        self.assertTrue(forecasts[0]['is_positive'])
        
        # Month 3 projection should be 130,000
        self.assertEqual(forecasts[2]['value'], 130000.0)

    def test_forecast_negative_trend(self):
        """Test forecast with negative savings (Expense > Income)."""
        # 3 months of 5k deficit each
        self._create_history(Decimal('30000.00'), Decimal('35000.00'), months=3)
        
        response = self.client.get(reverse('home'))
        
        forecasts = response.context['net_worth_forecasts']
        # Current NW is 100,000. Avg savings is -5,000.
        self.assertEqual(forecasts[0]['value'], 95000.0)
        self.assertEqual(forecasts[0]['change'], -5000.0)
        self.assertFalse(forecasts[0]['is_positive'])

    def test_forecast_no_history(self):
        """Test forecast for new user with no history."""
        response = self.client.get(reverse('home'))
        
        forecasts = response.context['net_worth_forecasts']
        # Should show 3 months of current net worth (100,000) with 0 change
        self.assertEqual(len(forecasts), 3)
        self.assertEqual(forecasts[0]['value'], 100000.0)
        self.assertEqual(forecasts[0]['change'], 0.0)
        self.assertTrue(forecasts[0]['is_positive']) # 0 is treated as positive in my logic (>= 0)

    def test_forecast_context_keys(self):
        """Ensure all required template keys are present in forecast objects."""
        self._create_history(Decimal('1000.00'), Decimal('500.00'), months=1)
        
        response = self.client.get(reverse('home'))
        forecast = response.context['net_worth_forecasts'][0]
        
        self.assertIn('label', forecast)     # e.g. 'May'
        self.assertIn('month_name', forecast) # e.g. 'May 2026'
        self.assertIn('value', forecast)
        self.assertIn('change', forecast)
        self.assertIn('is_positive', forecast)
