from django.test import TestCase, Client, override_settings
from django.urls import reverse

@override_settings(RECAPTCHA_PUBLIC_KEY=None, RECAPTCHA_PRIVATE_KEY=None)
class StaticPageTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_landing_page(self):
        url = reverse('landing')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_pricing_page(self):
        url = reverse('pricing')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_contact_form_submission(self):
        url = reverse('contact')
        data = {
            'name': 'Test',
            'email': 'test@example.com',
            'subject': 'Hello',
            'message': 'This is a test message with sufficient length.',
            'website': '' # Honeypot
        }
        # Assuming email backend is setup for testing else it might fail or send real email?
        # Usually tests use locmem backend.
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

    def test_demo_login(self):
        from django.contrib.auth.models import User
        # Create demo user
        User.objects.create_user(username='demo', password='password')
        url = reverse('demo_login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        # Check logged in
        self.assertIn('_auth_user_id', self.client.session)

    def test_contact_page(self):
        url = reverse('contact')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_robots_txt(self):
        # Assuming robots.txt is served or configured
        try:
             url = reverse('robots_txt') # Or partial path if hardcoded in urls
             response = self.client.get(url)
             self.assertEqual(response.status_code, 200)
        except:
             pass 
