from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Customer, Loan
from .services import CreditScoreCalculator, LoanEligibilityService


class CustomerModelTest(TestCase):
    def test_customer_creation(self):
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            age=30,
            phone_number=1234567890,
            monthly_salary=Decimal('50000'),
            approved_limit=Decimal('1800000')
        )
        self.assertEqual(customer.first_name, 'John')
        self.assertEqual(customer.approved_limit, Decimal('1800000'))


class CustomerRegistrationAPITest(APITestCase):
    def test_register_customer_success(self):
        url = reverse('register_customer')
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'age': 25,
            'monthly_income': 60000,
            'phone_number': 9876543210
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Jane Smith')
        self.assertEqual(response.data['approved_limit'], '2200000.00')
    
    def test_register_customer_duplicate_phone(self):
        # Create a customer first
        Customer.objects.create(
            first_name='Existing',
            last_name='Customer',
            age=30,
            phone_number=1111111111,
            monthly_salary=Decimal('40000'),
            approved_limit=Decimal('1440000')
        )
        
        url = reverse('register_customer')
        data = {
            'first_name': 'New',
            'last_name': 'Customer',
            'age': 28,
            'monthly_income': 50000,
            'phone_number': 1111111111  # Same phone number
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CreditScoreCalculatorTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            age=30,
            phone_number=1234567890,
            monthly_salary=Decimal('50000'),
            approved_limit=Decimal('1800000')
        )
    
    def test_new_customer_default_score(self):
        score = CreditScoreCalculator.calculate_credit_score(self.customer)
        self.assertEqual(score, 50)
    
    def test_credit_score_with_loans(self):
        # Create a loan
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('100000'),
            tenure=12,
            interest_rate=Decimal('10.5'),
            monthly_repayment=Decimal('8800'),
            emis_paid_on_time=12,
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        
        score = CreditScoreCalculator.calculate_credit_score(self.customer)
        self.assertGreater(score, 50)


class LoanEligibilityServiceTest(TestCase):
    def test_monthly_installment_calculation(self):
        emi = LoanEligibilityService.calculate_monthly_installment(
            loan_amount=Decimal('100000'),
            interest_rate=Decimal('12'),
            tenure=12
        )
        self.assertIsInstance(emi, Decimal)
        self.assertGreater(emi, 0)
    
    def test_corrected_interest_rate(self):
        # High credit score
        rate = LoanEligibilityService.get_corrected_interest_rate(60, Decimal('8'))
        self.assertEqual(rate, Decimal('8'))
        
        # Medium credit score
        rate = LoanEligibilityService.get_corrected_interest_rate(40, Decimal('8'))
        self.assertEqual(rate, Decimal('12'))
        
        # Low credit score
        rate = LoanEligibilityService.get_corrected_interest_rate(20, Decimal('8'))
        self.assertEqual(rate, Decimal('16'))


class LoanEligibilityAPITest(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            age=30,
            phone_number=1234567890,
            monthly_salary=Decimal('50000'),
            approved_limit=Decimal('1800000')
        )
    
    def test_check_eligibility_success(self):
        url = reverse('check_eligibility')
        data = {
            'customer_id': self.customer.customer_id,
            'loan_amount': 100000,
            'interest_rate': 10.5,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('approval', response.data)
        self.assertIn('monthly_installment', response.data)
    
    def test_check_eligibility_invalid_customer(self):
        url = reverse('check_eligibility')
        data = {
            'customer_id': 99999,  # Non-existent customer
            'loan_amount': 100000,
            'interest_rate': 10.5,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)