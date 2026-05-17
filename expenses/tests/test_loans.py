import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from expenses.models import Account, Loan, LoanInterestRate, LoanRepayment
from expenses.services import LoanService

class LoanServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='loan_test', password='password')
        self.account = Account.objects.create(
            user=self.user,
            name='Test Bank',
            account_type='BANK',
            balance=Decimal('100000.00'),
            currency='₹'
        )
        self.loan = Loan.objects.create(
            user=self.user,
            name='Test Home Loan',
            loan_type='HOME',
            initial_principal=Decimal('50000.00'),
            duration_months=12,
            start_date=datetime.date(2023, 1, 1),
            currency='₹'
        )
        self.rate = LoanInterestRate.objects.create(
            loan=self.loan,
            interest_rate=Decimal('12.00'),
            effective_date=datetime.date(2023, 1, 1)
        )

    def test_calculate_emi(self):
        # 50,000 at 12% for 12 months -> EMI = P*r*(1+r)^n/((1+r)^n-1)
        # r = 0.01 (1%), P = 50000, n = 12
        # EMI ~ 4442.44
        emi = LoanService.calculate_emi(50000, 12, 12)
        self.assertAlmostEqual(emi, 4442.44, places=1)
        
        # Test 0 interest
        emi_zero_interest = LoanService.calculate_emi(50000, 0, 12)
        self.assertEqual(emi_zero_interest, 50000 / 12.0)

    def test_amortization_schedule(self):
        # Schedule with no payments made
        schedule = LoanService.generate_amortization_schedule(self.loan)
        # Should generate 12 payments because duration is 12 and 0 payments made, 
        # wait, the logic uses `today` to find months_passed. This might be problematic in tests if `today` > 2023.
        # Let's mock today or update the loan start date to today
        
        self.loan.start_date = datetime.date.today()
        self.loan.save()
        
        schedule = LoanService.generate_amortization_schedule(self.loan)
        self.assertEqual(len(schedule), 12)
        
        first_month = schedule[0]
        self.assertAlmostEqual(first_month['emi'], 4442.44, places=1)
        self.assertAlmostEqual(first_month['interest'], 500.00, places=1)  # 50000 * 0.01
        self.assertAlmostEqual(first_month['principal'], 3942.44, places=1)

    def test_repayment_deducts_from_account(self):
        initial_balance = self.account.balance
        
        repayment = LoanRepayment.objects.create(
            loan=self.loan,
            from_account=self.account,
            amount=Decimal('4442.44'),
            principal_portion=Decimal('3942.44'),
            interest_portion=Decimal('500.00'),
            date=datetime.date.today()
        )
        
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, initial_balance - Decimal('4442.44'))
        
        # Test reverse on delete
        repayment.delete()
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, initial_balance)

    def test_floating_interest_rate(self):
        # Start loan today
        self.loan.start_date = datetime.date.today()
        self.loan.save()
        
        # Change rate
        LoanInterestRate.objects.create(
            loan=self.loan,
            interest_rate=Decimal('24.00'), # 2% per month
            effective_date=datetime.date.today()
        )
        
        schedule = LoanService.generate_amortization_schedule(self.loan)
        first_month = schedule[0]
        # At 24% (2% per month), interest on 50000 is 1000
        self.assertAlmostEqual(first_month['interest'], 1000.00, places=1)
        
    def test_total_liabilities(self):
        # Make a repayment to reduce principal
        LoanRepayment.objects.create(
            loan=self.loan,
            from_account=self.account,
            amount=Decimal('4442.44'),
            principal_portion=Decimal('3942.44'),
            interest_portion=Decimal('500.00'),
            date=datetime.date.today()
        )
        
        # Expected remaining principal: 50000 - 3942.44 = 46057.56
        total = LoanService.get_total_liabilities(self.user)
        self.assertAlmostEqual(float(total), 46057.56, places=1)

    def test_loan_create_page_shows_emi_preview_calculator(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('loan-create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="emi-preview-value"')
        self.assertContains(response, 'id="emi-preview-hint"')
        self.assertContains(response, 'function calculateEmi')
