import json
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from expenses.models import PaymentHistory, SubscriptionPlan, UserProfile


class RazorpaySubscriptionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='subuser', password='password', email='sub@example.com')
        self.profile = self.user.profile
        self.client = Client()
        self.client.login(username='subuser', password='password')

        # Create test plans
        self.plus_monthly = SubscriptionPlan.objects.create(
            tier='PLUS', duration='MONTHLY', name='Plus Monthly',
            price=49, is_active=True
        )
        self.pro_monthly = SubscriptionPlan.objects.create(
            tier='PRO', duration='MONTHLY', name='Pro Monthly',
            price=99, is_active=True
        )

    @patch('expenses.management.commands.sync_razorpay_plans.razorpay.Client')
    def test_sync_plans_management_command(self, MockRazorpayClient):
        """Test that sync_razorpay_plans creates plans on Razorpay and updates DB."""
        mock_client_instance = MockRazorpayClient.return_value
        mock_client_instance.plan.create.return_value = {'id': 'plan_test_123'}

        out = StringIO()
        call_command('sync_razorpay_plans', stdout=out)

        self.assertIn('Successfully created Razorpay plan', out.getvalue())
        self.plus_monthly.refresh_from_db()
        self.assertEqual(self.plus_monthly.razorpay_plan_id, 'plan_test_123')

    @patch('expenses.views_payment.razorpay.Client')
    def test_create_order_uses_subscription_when_plan_exists(self, MockRazorpayClient):
        """If a Razorpay plan ID exists, create_order should use client.subscription.create."""
        self.plus_monthly.razorpay_plan_id = 'plan_plus_123'
        self.plus_monthly.save()

        mock_client_instance = MockRazorpayClient.return_value
        mock_client_instance.subscription.create.return_value = {'id': 'sub_123', 'status': 'created'}

        url = reverse('create-order')
        data = {'plan_type': 'PLUS', 'duration': 'MONTHLY'}
        response = self.client.post(url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['type'], 'SUBSCRIPTION')
        self.assertEqual(response.json()['id'], 'sub_123')
        
        # Verify PaymentHistory created with Subscription ID
        self.assertTrue(PaymentHistory.objects.filter(order_id='sub_123').exists())

    @patch('expenses.views_payment.razorpay.Client')
    def test_create_order_falls_back_to_order_when_plan_missing(self, MockRazorpayClient):
        """If plan ID is missing, fall back to one-time order creation."""
        mock_client_instance = MockRazorpayClient.return_value
        mock_client_instance.order.create.return_value = {'id': 'order_123', 'status': 'created'}

        url = reverse('create-order')
        data = {'plan_type': 'PRO', 'duration': 'MONTHLY'} # pro_monthly has no razorpay_plan_id
        response = self.client.post(url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['type'], 'ORDER')
        self.assertEqual(response.json()['id'], 'order_123')

    @patch('expenses.views_payment.razorpay.Client')
    def test_verify_subscription_payment(self, MockRazorpayClient):
        """Verify subscription payment signature and update profile."""
        PaymentHistory.objects.create(
            user=self.user, order_id='sub_123', amount=49,
            tier='PLUS', duration='MONTHLY', status='PENDING'
        )

        mock_client_instance = MockRazorpayClient.return_value
        mock_client_instance.utility.verify_payment_signature.return_value = None

        url = reverse('verify-payment')
        data = {
            'razorpay_subscription_id': 'sub_123',
            'razorpay_payment_id': 'pay_123',
            'razorpay_signature': 'sig_123'
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.tier, 'PLUS')
        self.assertEqual(self.profile.razorpay_subscription_id, 'sub_123')
        self.assertTrue(self.profile.subscription_end_date > timezone.now())

    @patch('expenses.views_payment.razorpay.Client')
    def test_webhook_subscription_charged(self, MockRazorpayClient):
        """Webhook should extend subscription_end_date on subscription.charged event."""
        self.profile.razorpay_subscription_id = 'sub_999'
        self.profile.tier = 'PRO'
        self.profile.save()

        # Mock webhook signature verification
        mock_client_instance = MockRazorpayClient.return_value
        mock_client_instance.utility.verify_webhook_signature.return_value = True

        # Mock settings for webhook secret
        with self.settings(RAZORPAY_WEBHOOK_SECRET='test_secret'):
            # Event Payload
            new_end_timestamp = int((timezone.now() + timedelta(days=32)).timestamp())
            payload = {
                'event': 'subscription.charged',
                'payload': {
                    'subscription': {
                        'entity': {
                            'id': 'sub_999',
                            'current_end': new_end_timestamp
                        }
                    },
                    'payment': {
                        'entity': {
                            'id': 'pay_charged_123',
                            'amount': 9900
                        }
                    }
                }
            }

            url = reverse('razorpay-webhook')
            response = self.client.post(
                url, json.dumps(payload), content_type='application/json',
                HTTP_X_RAZORPAY_SIGNATURE='valid_sig'
            )

            self.assertEqual(response.status_code, 200)
            self.profile.refresh_from_db()
            
            # Check if end date updated
            self.assertEqual(int(self.profile.subscription_end_date.timestamp()), new_end_timestamp)
            
            # Check if new payment logged
            self.assertTrue(PaymentHistory.objects.filter(payment_id='pay_charged_123').exists())

    @patch('expenses.views_payment.razorpay.Client')
    def test_cancel_subscription(self, MockRazorpayClient):
        """Test cancelling a subscription via the API."""
        self.profile.razorpay_subscription_id = 'sub_cancel_123'
        self.profile.save()

        mock_client_instance = MockRazorpayClient.return_value
        mock_client_instance.subscription.cancel.return_value = {'id': 'sub_cancel_123', 'status': 'cancelled'}

        url = reverse('cancel-subscription')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Verify Razorpay cancel called with correct arguments
        mock_client_instance.subscription.cancel.assert_called_with('sub_cancel_123', {'cancel_at_cycle_end': 1})
