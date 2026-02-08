from django.test import TestCase
from django.contrib.auth.models import User
from django.core.cache import cache
from decimal import Decimal
from unittest.mock import patch, MagicMock
import requests
from expenses.models import Expense, Income, UserProfile
from expenses.utils import get_exchange_rate

class CurrencyConversionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        if not hasattr(self.user, 'profile'):
            UserProfile.objects.create(user=self.user, currency='₹') # Base is INR
        else:
            self.user.profile.currency = '₹'
            self.user.profile.save()
        
        # Clear cache before each test
        cache.clear()

    @patch('requests.get')
    def test_identity_conversion(self, mock_get):
        """Converting same currency should return 1.0 and not call API."""
        rate = get_exchange_rate('₹', '₹')
        self.assertEqual(rate, Decimal('1.0'))
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_successful_conversion_api(self, mock_get):
        """Test successful API call and base_amount calculation."""
        # Mock API response for USD to INR
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'rates': {'INR': 83.50}}
        mock_get.return_value = mock_response

        # 1. Test utility directly
        rate = get_exchange_rate('$', '₹')
        self.assertEqual(rate, Decimal('83.50'))
        
        # 2. Test Model Integration (Expense)
        obj = Expense.objects.create(
            user=self.user,
            date='2024-01-01',
            amount=Decimal('10.00'),
            currency='$',
            description='Test USD Expense',
            category='Food'
        )
        self.assertEqual(obj.exchange_rate, Decimal('83.50'))
        self.assertEqual(obj.base_amount, Decimal('835.00'))

    @patch('requests.get')
    def test_conversion_caching(self, mock_get):
        """Verify that exchange rates are cached and API is only called once."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'rates': {'INR': 80.00}}
        mock_get.return_value = mock_response

        # First call hits API
        rate1 = get_exchange_rate('$', '₹')
        self.assertEqual(rate1, Decimal('80.00'))
        self.assertEqual(mock_get.call_count, 1)

        # Second call hits cache
        rate2 = get_exchange_rate('$', '₹')
        self.assertEqual(rate2, Decimal('80.00'))
        self.assertEqual(mock_get.call_count, 1)

    @patch('requests.get')
    def test_api_failure_fallback(self, mock_get):
        """If API fails (e.g., 500 error), it should fallback to 1.0."""
        mock_get.side_effect = requests.exceptions.HTTPError("API Down")
        
        rate = get_exchange_rate('$', '₹')
        self.assertEqual(rate, Decimal('1.0'))
        
        # Verify transaction still saves with 1.0
        obj = Expense.objects.create(
            user=self.user,
            date='2024-01-01',
            amount=Decimal('50.00'),
            currency='$',
            description='Fallback Test'
        )
        self.assertEqual(obj.exchange_rate, Decimal('1.0'))
        self.assertEqual(obj.base_amount, Decimal('50.00'))

    @patch('requests.get')
    def test_malformed_json_fallback(self, mock_get):
        """Handle cases where API returns invalid JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        rate = get_exchange_rate('$', '₹')
        self.assertEqual(rate, Decimal('1.0'))

    @patch('requests.get')
    def test_precision_preservation(self, mock_get):
        """Ensure high precision rates are saved correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # A rate with many decimal places
        complex_rate = 83.123456
        mock_response.json.return_value = {'rates': {'INR': complex_rate}}
        mock_get.return_value = mock_response

        obj = Income.objects.create(
            user=self.user,
            date='2024-01-01',
            amount=Decimal('100.00'),
            currency='$',
            source='Freelance'
        )
        self.assertEqual(obj.exchange_rate, Decimal('83.123456'))
        # 100 * 83.123456 = 8312.3456 -> Rounded to 8312.35 in DecimalField(decimal_places=2)
        self.assertEqual(obj.base_amount, Decimal('8312.35'))

    def test_unsupported_currency_symbol(self, mock_get=None):
        """If a symbol is unknown, it should attempt to use literal or fallback."""
        # 'XYZ' is not in our mapping
        rate = get_exchange_rate('XYZ', 'INR')
        self.assertEqual(rate, Decimal('1.0')) # Should fallback gracefully
