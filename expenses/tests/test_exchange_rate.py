
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase

from expenses.utils import get_exchange_rate


class ExchangeRateFallbackTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch('requests.get')
    def test_frankfurter_success(self, mock_get):
        # Mock successful Frankfurter response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'rates': {'USD': 0.012}
        }
        mock_get.return_value = mock_response

        rate = get_exchange_rate('₹', '$')
        
        self.assertEqual(rate, Decimal('0.012'))
        # Ensure Frankfurter was called
        mock_get.assert_called_with("https://api.frankfurter.app/latest?from=INR&to=USD", timeout=5)
        # Ensure it was cached
        self.assertEqual(cache.get("xr_INR_USD"), 0.012)

    @patch('requests.get')
    def test_frankfurter_fails_fallback_success(self, mock_get):
        # Mock Frankfurter failure then ExchangeRate-API success
        mock_frankfurter = MagicMock()
        mock_frankfurter.status_code = 500
        mock_frankfurter.raise_for_status.side_effect = Exception("Frankfurter Down")
        
        mock_fallback = MagicMock()
        mock_fallback.status_code = 200
        mock_fallback.json.return_value = {
            'rates': {'USD': 0.013}
        }
        
        mock_get.side_effect = [mock_frankfurter, mock_fallback]

        rate = get_exchange_rate('₹', '$')
        
        self.assertEqual(rate, Decimal('0.013'))
        # Ensure both were called
        self.assertEqual(mock_get.call_count, 2)
        mock_get.assert_any_call("https://api.frankfurter.app/latest?from=INR&to=USD", timeout=5)
        mock_get.assert_any_call("https://api.exchangerate-api.com/v4/latest/INR", timeout=5)
        # Ensure it was cached
        self.assertEqual(cache.get("xr_INR_USD"), 0.013)

    @patch('requests.get')
    def test_both_fail_returns_one(self, mock_get):
        # Mock both failing
        mock_get.side_effect = Exception("All APIs Down")

        rate = get_exchange_rate('₹', '$')
        
        self.assertEqual(rate, Decimal('1.0'))
        # Ensure both were called (or at least attempted)
        self.assertEqual(mock_get.call_count, 2)
        # Ensure NOT cached on total failure
        self.assertIsNone(cache.get("xr_INR_USD"))

    def test_same_currency(self):
        # Should return 1.0 without calling any API
        rate = get_exchange_rate('₹', '₹')
        self.assertEqual(rate, Decimal('1.0'))

    @patch('requests.get')
    def test_cache_hits(self, mock_get):
        # Pre-populate cache
        cache.set("xr_INR_USD", 0.015)
        
        rate = get_exchange_rate('₹', '$')
        
        self.assertEqual(rate, Decimal('0.015'))
        # Ensure API was NOT called
        mock_get.assert_not_called()
