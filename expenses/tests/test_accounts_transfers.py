from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from expenses.models import Account, Transfer, Expense, Income, Category
from datetime import date
from decimal import Decimal

class AccountTransferTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        # Ensure profile exists and tutorial is seen
        profile = self.user.profile
        profile.has_seen_tutorial = True
        profile.tier = 'PLUS'
        profile.save()
        
        # Create categories
        self.food_cat, _ = Category.objects.get_or_create(user=self.user, name='Food', defaults={'limit': 1000})
        
        # Create accounts
        self.bank = Account.objects.create(user=self.user, name='Bank', account_type='BANK', balance=Decimal('5000.00'))
        self.cash = Account.objects.create(user=self.user, name='Cash', account_type='CASH', balance=Decimal('1000.00'))
        self.cc = Account.objects.create(user=self.user, name='Credit Card', account_type='CREDIT_CARD', balance=Decimal('-500.00'))

    def test_income_updates_account_balance(self):
        Income.objects.create(
            user=self.user,
            date=date.today(),
            amount=Decimal('500.00'),
            source='Freelance',
            account=self.bank
        )
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal('5500.00'))

    def test_income_update_reverts_old_balance(self):
        income = Income.objects.create(
            user=self.user,
            date=date.today(),
            amount=Decimal('500.00'),
            source='Freelance',
            account=self.bank
        )
        # Update amount
        income.amount = Decimal('700.00')
        income.save()
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal('5700.00'))
        
        # Switch account
        income.account = self.cash
        income.amount = Decimal('200.00')
        income.save()
        
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal('5000.00'))
        self.assertEqual(self.cash.balance, Decimal('1200.00'))

    def test_expense_updates_account_balance(self):
        Expense.objects.create(
            user=self.user,
            date=date.today(),
            amount=Decimal('100.00'),
            category='Food',
            description='Lunch',
            account=self.bank
        )
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal('4900.00'))

    def test_transfer_protocol(self):
        # Transfer from Bank to Cash
        transfer = Transfer.objects.create(
            user=self.user,
            from_account=self.bank,
            to_account=self.cash,
            amount=Decimal('500.00'),
            date=date.today()
        )
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal('4500.00'))
        self.assertEqual(self.cash.balance, Decimal('1500.00'))

        # Update transfer
        transfer.amount = Decimal('200.00')
        transfer.save()
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal('4800.00'))
        self.assertEqual(self.cash.balance, Decimal('1200.00'))

        # Delete transfer
        transfer.delete()
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal('5000.00'))
        self.assertEqual(self.cash.balance, Decimal('1000.00'))

    def test_credit_card_spending_liability(self):
        # Spend on CC
        Expense.objects.create(
            user=self.user,
            date=date.today(),
            amount=Decimal('100.00'),
            category='Food',
            description='Dinner',
            account=self.cc
        )
        self.cc.refresh_from_db()
        self.assertEqual(self.cc.balance, Decimal('-600.00'))
        
        # Pay CC bill from Bank
        Transfer.objects.create(
            user=self.user,
            from_account=self.bank,
            to_account=self.cc,
            amount=Decimal('600.00'),
            date=date.today()
        )
        self.bank.refresh_from_db()
        self.cc.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal('4400.00'))
        self.assertEqual(self.cc.balance, Decimal('0.00'))

    def test_view_account_crud(self):
        # List
        response = self.client.get(reverse('account-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bank')
        
        # Create
        response = self.client.post(reverse('account-create'), {
            'name': 'New Wallet',
            'account_type': 'CASH',
            'balance': '100.00',
            'currency': '₹'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Account.objects.filter(name='New Wallet').exists())
        
        # Edit
        account = Account.objects.get(name='New Wallet')
        response = self.client.post(reverse('account-edit', kwargs={'pk': account.pk}), {
            'name': 'Updated Wallet',
            'account_type': 'CASH',
            'balance': '200.00',
            'currency': '₹'
        })
        self.assertEqual(response.status_code, 302)
        account.refresh_from_db()
        self.assertEqual(account.name, 'Updated Wallet')
        
        # Delete
        response = self.client.post(reverse('account-delete', kwargs={'pk': account.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Account.objects.filter(name='Updated Wallet').exists())

    def test_view_transfer_crud(self):
        # Create via view
        response = self.client.post(reverse('transfer-create'), {
            'from_account': self.bank.pk,
            'to_account': self.cash.pk,
            'amount': '300.00',
            'date': date.today().strftime('%Y-%m-%d'),
            'description': 'View transfer'
        })
        self.assertEqual(response.status_code, 302)
        transfer = Transfer.objects.get(description='View transfer')
        self.assertEqual(transfer.amount, Decimal('300.00'))
        
        # List
        response = self.client.get(reverse('transfer-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View transfer')
        
        # Edit
        response = self.client.post(reverse('transfer-edit', kwargs={'pk': transfer.pk}), {
            'from_account': self.bank.pk,
            'to_account': self.cash.pk,
            'amount': '400.00',
            'date': date.today().strftime('%Y-%m-%d'),
            'description': 'Updated transfer'
        })
        self.assertEqual(response.status_code, 302)
        transfer.refresh_from_db()
        self.assertEqual(transfer.amount, Decimal('400.00'))
        
        # Delete
        response = self.client.post(reverse('transfer-delete', kwargs={'pk': transfer.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Transfer.objects.filter(pk=transfer.pk).exists())
