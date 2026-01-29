"""
Tests for SharedExpense form functionality.
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from expenses.forms import ExpenseForm
from expenses.models import Category


class ExpenseFormTestCase(TestCase):
    """Test cases for ExpenseForm with shared expense support."""

    def setUp(self):
        """Set up test user and category."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        # Use get_or_create to avoid unique constraint violations
        self.category, _ = Category.objects.get_or_create(user=self.user, name="Food")

    def test_form_has_expense_type_field(self):
        """Test that form includes expense_type field."""
        form = ExpenseForm(user=self.user)
        self.assertIn("expense_type", form.fields)
        self.assertEqual(form.fields["expense_type"].initial, "personal")

    def test_form_has_participants_json_field(self):
        """Test that form includes participants_json hidden field."""
        form = ExpenseForm(user=self.user)
        self.assertIn("participants_json", form.fields)
        self.assertFalse(form.fields["participants_json"].required)

    def test_form_has_payer_id_field(self):
        """Test that form includes payer_id hidden field."""
        form = ExpenseForm(user=self.user)
        self.assertIn("payer_id", form.fields)
        self.assertFalse(form.fields["payer_id"].required)

    def test_form_prepopulates_user_as_first_participant(self):
        """Test that user is pre-populated as first participant."""
        form = ExpenseForm(user=self.user)
        participants_json = form.fields["participants_json"].initial
        participants = json.loads(participants_json)

        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0]["name"], "testuser")
        self.assertTrue(participants[0]["is_user"])

    def test_personal_expense_validation_passes(self):
        """Test that personal expense validation works."""
        form_data = {
            "expense_type": "personal",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_shared_expense_requires_participants(self):
        """Test that shared expense requires participants_json."""
        form_data = {
            "expense_type": "shared",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test shared expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
            "participants_json": "",
            "payer_id": "testuser",
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("participants_json", form.errors)

    def test_shared_expense_requires_minimum_two_participants(self):
        """Test that shared expense requires at least 2 participants."""
        participants = [{"name": "testuser", "is_user": True, "share_amount": "100.00"}]
        form_data = {
            "expense_type": "shared",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test shared expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
            "participants_json": json.dumps(participants),
            "payer_id": "testuser",
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("participants_json", form.errors)

    def test_shared_expense_validates_share_sum_equals_total(self):
        """Test that share amounts must sum to total expense amount."""
        participants = [
            {"name": "testuser", "is_user": True, "share_amount": "50.00"},
            {"name": "Alice", "is_user": False, "share_amount": "30.00"},
        ]
        form_data = {
            "expense_type": "shared",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test shared expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
            "participants_json": json.dumps(participants),
            "payer_id": "testuser",
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Share amounts must sum to total expense amount", str(form.errors)
        )

    def test_shared_expense_validates_payer_is_participant(self):
        """Test that payer must be one of the participants."""
        participants = [
            {"name": "testuser", "is_user": True, "share_amount": "50.00"},
            {"name": "Alice", "is_user": False, "share_amount": "50.00"},
        ]
        form_data = {
            "expense_type": "shared",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test shared expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
            "participants_json": json.dumps(participants),
            "payer_id": "Bob",  # Bob is not a participant
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("payer_id", form.errors)

    def test_shared_expense_rejects_duplicate_participant_names(self):
        """Test that duplicate participant names are rejected."""
        participants = [
            {"name": "testuser", "is_user": True, "share_amount": "50.00"},
            {"name": "testuser", "is_user": False, "share_amount": "50.00"},
        ]
        form_data = {
            "expense_type": "shared",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test shared expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
            "participants_json": json.dumps(participants),
            "payer_id": "testuser",
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("participants_json", form.errors)

    def test_shared_expense_rejects_empty_participant_names(self):
        """Test that empty participant names are rejected."""
        participants = [
            {"name": "testuser", "is_user": True, "share_amount": "50.00"},
            {"name": "  ", "is_user": False, "share_amount": "50.00"},
        ]
        form_data = {
            "expense_type": "shared",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test shared expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
            "participants_json": json.dumps(participants),
            "payer_id": "testuser",
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("participants_json", form.errors)

    def test_valid_shared_expense_passes_validation(self):
        """Test that a valid shared expense passes all validation."""
        participants = [
            {"name": "testuser", "is_user": True, "share_amount": "50.00"},
            {"name": "Alice", "is_user": False, "share_amount": "50.00"},
        ]
        form_data = {
            "expense_type": "shared",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test shared expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
            "participants_json": json.dumps(participants),
            "payer_id": "testuser",
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_shared_expense_validates_positive_share_amounts(self):
        """Test that share amounts must be positive."""
        participants = [
            {"name": "testuser", "is_user": True, "share_amount": "50.00"},
            {"name": "Alice", "is_user": False, "share_amount": "-50.00"},
        ]
        form_data = {
            "expense_type": "shared",
            "date": "2024-01-15",
            "amount": "100.00",
            "description": "Test shared expense",
            "category": "Food",
            "payment_method": "Cash",
            "has_cashback": False,
            "participants_json": json.dumps(participants),
            "payer_id": "testuser",
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("participants_json", form.errors)
