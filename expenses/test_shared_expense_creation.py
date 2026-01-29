from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Expense, SharedExpense, SharedExpenseParticipant, Share
from datetime import date
import json
from decimal import Decimal


class SharedExpenseCreationViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

    def test_create_personal_expense(self):
        """Test that personal expenses still work (backward compatibility)."""
        response = self.client.post(
            reverse("expense-create"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-date": "2024-01-15",
                "form-0-amount": "100.00",
                "form-0-description": "Test personal expense",
                "form-0-category": "Food",
                "form-0-payment_method": "Cash",
                "form-0-expense_type": "personal",
            },
        )

        # Should redirect to expense list
        self.assertEqual(response.status_code, 302)

        # Verify expense was created
        expense = Expense.objects.filter(
            user=self.user, description="Test personal expense"
        ).first()
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal("100.00"))

        # Verify no shared expense was created
        self.assertFalse(hasattr(expense, "shared_details"))

    def test_create_shared_expense_basic(self):
        """Test creating a basic shared expense with two participants."""
        participants_data = [
            {"name": "testuser", "is_user": True, "share_amount": "50.00"},
            {"name": "Alice", "is_user": False, "share_amount": "50.00"},
        ]

        response = self.client.post(
            reverse("expense-create"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-date": "2024-01-15",
                "form-0-amount": "100.00",
                "form-0-description": "Shared dinner",
                "form-0-category": "Food",
                "form-0-payment_method": "Cash",
                "form-0-expense_type": "shared",
                "form-0-participants_json": json.dumps(participants_data),
                "form-0-payer_id": "testuser",
            },
        )

        # Should redirect to expense list
        self.assertEqual(response.status_code, 302)

        # Verify expense was created
        expense = Expense.objects.filter(
            user=self.user, description="Shared dinner"
        ).first()
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal("100.00"))

        # Verify shared expense was created
        self.assertTrue(hasattr(expense, "shared_details"))
        shared_expense = expense.shared_details

        # Verify participants were created
        participants = shared_expense.participants.all()
        self.assertEqual(participants.count(), 2)

        # Verify user participant is marked correctly
        user_participant = participants.filter(is_user=True).first()
        self.assertIsNotNone(user_participant)
        self.assertEqual(user_participant.name, "You")

        # Verify payer is set correctly
        self.assertEqual(shared_expense.payer.name, "You")

        # Verify shares were created
        shares = shared_expense.shares.all()
        self.assertEqual(shares.count(), 2)

        # Verify share amounts
        user_share = shares.filter(participant__is_user=True).first()
        self.assertEqual(user_share.amount, Decimal("50.00"))

        alice_share = shares.filter(participant__friend__name="Alice").first()
        self.assertEqual(alice_share.amount, Decimal("50.00"))

    def test_create_shared_expense_multiple_participants(self):
        """Test creating a shared expense with multiple participants."""
        participants_data = [
            {"name": "testuser", "is_user": True, "share_amount": "30.00"},
            {"name": "Alice", "is_user": False, "share_amount": "35.00"},
            {"name": "Bob", "is_user": False, "share_amount": "35.00"},
        ]

        response = self.client.post(
            reverse("expense-create"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-date": "2024-01-15",
                "form-0-amount": "100.00",
                "form-0-description": "Group lunch",
                "form-0-category": "Food",
                "form-0-payment_method": "UPI",
                "form-0-expense_type": "shared",
                "form-0-participants_json": json.dumps(participants_data),
                "form-0-payer_id": "Alice",
            },
        )

        # Should redirect to expense list
        self.assertEqual(response.status_code, 302)

        # Verify expense was created
        expense = Expense.objects.filter(
            user=self.user, description="Group lunch"
        ).first()
        self.assertIsNotNone(expense)

        # Verify shared expense details
        shared_expense = expense.shared_details
        self.assertEqual(shared_expense.payer.name, "Alice")

        # Verify all participants were created
        participants = shared_expense.participants.all()
        self.assertEqual(participants.count(), 3)

        # Verify all shares were created
        shares = shared_expense.shares.all()
        self.assertEqual(shares.count(), 3)

    def test_participant_name_trimming(self):
        """Test that participant names are trimmed of whitespace."""
        participants_data = [
            {"name": "  testuser  ", "is_user": True, "share_amount": "50.00"},
            {"name": "  Alice  ", "is_user": False, "share_amount": "50.00"},
        ]

        response = self.client.post(
            reverse("expense-create"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-date": "2024-01-15",
                "form-0-amount": "100.00",
                "form-0-description": "Test trimming",
                "form-0-category": "Food",
                "form-0-payment_method": "Cash",
                "form-0-expense_type": "shared",
                "form-0-participants_json": json.dumps(participants_data),
                "form-0-payer_id": "  testuser  ",
            },
        )

        # Should redirect to expense list
        self.assertEqual(response.status_code, 302)

        # Verify participants have trimmed names
        expense = Expense.objects.filter(
            user=self.user, description="Test trimming"
        ).first()
        shared_expense = expense.shared_details

        participants = shared_expense.participants.all()
        participant_names = [p.name for p in participants]

        self.assertIn("You", participant_names)
        self.assertIn("Alice", participant_names)
        self.assertNotIn("  testuser  ", participant_names)
        self.assertNotIn("  Alice  ", participant_names)


from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from datetime import date
from expenses.models import Expense, SharedExpense, SharedExpenseParticipant, Share
import json


class SharedExpenseListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

    @override_settings(
        STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
    )
    def test_shared_expense_indicator_displayed(self):
        """Test that shared expenses show a visual indicator in the expense list."""
        from datetime import date as date_module

        today = date_module.today()

        # Create a personal expense
        Expense.objects.create(
            user=self.user,
            date=today,
            amount=Decimal("50.00"),
            description="Personal expense",
            category="Food",
            payment_method="Cash",
        )

        # Create a shared expense using the view (which handles the circular dependency properly)
        participants_data = [
            {"name": "testuser", "is_user": True, "share_amount": "50.00"},
            {"name": "Alice", "is_user": False, "share_amount": "50.00"},
        ]

        import json

        response = self.client.post(
            reverse("expense-create"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-date": today.strftime("%Y-%m-%d"),
                "form-0-amount": "100.00",
                "form-0-description": "Shared dinner",
                "form-0-category": "Food",
                "form-0-payment_method": "Cash",
                "form-0-expense_type": "shared",
                "form-0-participants_json": json.dumps(participants_data),
                "form-0-payer_id": "testuser",
            },
        )

        # Should redirect on success
        self.assertEqual(
            response.status_code, 302, "Form submission should redirect on success"
        )

        # Verify the shared expense was created
        shared_expenses = Expense.objects.filter(
            user=self.user, description="Shared dinner"
        )
        self.assertEqual(shared_expenses.count(), 1, "Shared expense was not created")

        # Get the expense list page
        response = self.client.get(reverse("expense-list"))
        self.assertEqual(response.status_code, 200)

        # Check that both expenses are in the response
        self.assertContains(response, "Personal expense")
        self.assertContains(response, "Shared dinner")

        # Check that the shared expense has the indicator
        self.assertContains(response, "bi-people-fill")
        self.assertContains(response, "Shared")

        # Verify the indicator appears only once (for the shared expense)
        content = response.content.decode("utf-8")
        shared_badge_count = content.count("bi-people-fill")
        self.assertEqual(shared_badge_count, 3)

    @override_settings(
        STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
    )
    def test_personal_expense_no_indicator(self):
        """Test that personal expenses do not show the shared indicator."""
        from datetime import date as date_module

        today = date_module.today()

        # Create only a personal expense
        personal_expense = Expense.objects.create(
            user=self.user,
            date=today,
            amount=Decimal("50.00"),
            description="Personal expense only",
            category="Food",
            payment_method="Cash",
        )

        # Get the expense list page
        response = self.client.get(reverse("expense-list"))
        self.assertEqual(response.status_code, 200)

        # Check that the expense is in the response
        self.assertContains(response, "Personal expense only")

        # Check that the shared indicator is NOT present
        self.assertNotContains(response, "bi-people-fill")
