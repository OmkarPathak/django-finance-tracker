from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(CRON_SECRET='test-secret')
class LedgerCronEndpointTest(TestCase):
    def test_retry_endpoint_requires_secret(self):
        response = self.client.get(reverse('cron-ledger-retry-failures'))
        self.assertEqual(response.status_code, 403)

    def test_reconcile_endpoint_requires_secret(self):
        response = self.client.get(reverse('cron-ledger-reconcile'))
        self.assertEqual(response.status_code, 403)

    def test_maintenance_endpoint_requires_secret(self):
        response = self.client.get(reverse('cron-ledger-maintenance'))
        self.assertEqual(response.status_code, 403)

    @patch('expenses.views.notifications.call_command')
    def test_retry_endpoint_calls_command_with_limit(self, mock_call_command):
        response = self.client.get(
            reverse('cron-ledger-retry-failures'),
            {'secret': 'test-secret', 'limit': '150'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['limit'], 150)
        mock_call_command.assert_called_once_with('retry_ledger_shadow_failures', limit=150)

    @patch('expenses.views.notifications.call_command')
    def test_retry_endpoint_invalid_limit_falls_back_to_default(self, mock_call_command):
        response = self.client.get(
            reverse('cron-ledger-retry-failures'),
            {'secret': 'test-secret', 'limit': 'not-a-number'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['limit'], 200)
        mock_call_command.assert_called_once_with('retry_ledger_shadow_failures', limit=200)

    @patch('expenses.views.notifications.call_command')
    def test_reconcile_endpoint_calls_command_with_threshold(self, mock_call_command):
        response = self.client.get(
            reverse('cron-ledger-reconcile'),
            {'secret': 'test-secret', 'threshold': '0.05'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['threshold'], '0.05')
        mock_call_command.assert_called_once_with('reconcile_ledgers', threshold='0.05')

    @patch('expenses.views.notifications.call_command')
    def test_reconcile_endpoint_invalid_threshold_falls_back_to_default(self, mock_call_command):
        response = self.client.get(
            reverse('cron-ledger-reconcile'),
            {'secret': 'test-secret', 'threshold': 'bad-threshold'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['threshold'], '0.01')
        mock_call_command.assert_called_once_with('reconcile_ledgers', threshold='0.01')

    @patch('expenses.views.notifications.call_command')
    def test_maintenance_endpoint_calls_command_with_defaults(self, mock_call_command):
        response = self.client.get(
            reverse('cron-ledger-maintenance'),
            {'secret': 'test-secret'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['retry_limit'], 200)
        self.assertEqual(payload['threshold'], '0.01')
        mock_call_command.assert_called_once_with(
            'run_ledger_maintenance',
            retry_limit=200,
            reconcile=True,
            threshold='0.01',
        )

    @patch('expenses.views.notifications.call_command')
    def test_maintenance_endpoint_calls_command_with_custom_params(self, mock_call_command):
        response = self.client.get(
            reverse('cron-ledger-maintenance'),
            {'secret': 'test-secret', 'retry_limit': '75', 'threshold': '0.1'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['retry_limit'], 75)
        self.assertEqual(payload['threshold'], '0.1')
        mock_call_command.assert_called_once_with(
            'run_ledger_maintenance',
            retry_limit=75,
            reconcile=True,
            threshold='0.1',
        )
