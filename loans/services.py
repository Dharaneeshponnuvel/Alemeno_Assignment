from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from .models import Customer, Loan


class CreditScoreCalculator:
    @staticmethod
    def calculate_credit_score(customer):
        """
        Calculate credit score based on historical loan data
        Components:
        i. Past Loans paid on time
        ii. No of loans taken in past
        iii. Loan activity in current year
        iv. Loan approved volume
        v. If sum of current loans > approved limit, credit score = 0
        """
        customer_loans = Loan.objects.filter(customer=customer)
        
        if not customer_loans.exists():
            return 50  # Default score for new customers
        
        # Check if current debt exceeds approved limit
        total_current_loans = customer_loans.aggregate(
            total=Sum('loan_amount')
        )['total'] or Decimal('0')
        
        if total_current_loans > customer.approved_limit:
            return 0
        
        # Calculate components
        total_loans = customer_loans.count()
        if total_loans == 0:
            return 50
        
        # Component 1: Past loans paid on time (40% weight)
        total_emis = customer_loans.aggregate(
            total=Sum('tenure')
        )['total'] or 0
        
        total_paid_on_time = customer_loans.aggregate(
            total=Sum('emis_paid_on_time')
        )['total'] or 0
        
        on_time_ratio = total_paid_on_time / max(total_emis, 1)
        on_time_score = min(40, on_time_ratio * 40)
        
        # Component 2: Number of loans taken (20% weight)
        # Fewer loans = better score
        loan_count_score = max(0, 20 - (total_loans * 2))
        
        # Component 3: Loan activity in current year (20% weight)
        current_year = timezone.now().year
        current_year_loans = customer_loans.filter(
            start_date__year=current_year
        ).count()
        
        # More recent activity = better score (up to a point)
        activity_score = min(20, current_year_loans * 5)
        
        # Component 4: Loan approved volume (20% weight)
        total_approved_volume = customer_loans.aggregate(
            total=Sum('loan_amount')
        )['total'] or Decimal('0')
        
        # Higher volume with good repayment = better score
        volume_ratio = min(1, float(total_approved_volume) / float(customer.approved_limit))
        volume_score = volume_ratio * 20
        
        total_score = on_time_score + loan_count_score + activity_score + volume_score
        return min(100, max(0, total_score))


class LoanEligibilityService:
    @staticmethod
    def calculate_monthly_installment(loan_amount, interest_rate, tenure):
        """
        Calculate EMI using compound interest formula
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        """
        principal = float(loan_amount)
        monthly_rate = float(interest_rate) / (12 * 100)
        
        if monthly_rate == 0:
            return Decimal(str(principal / tenure)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        
        emi = principal * monthly_rate * (1 + monthly_rate)**tenure / (
            (1 + monthly_rate)**tenure - 1
        )
        
        return Decimal(str(emi)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def get_corrected_interest_rate(credit_score, requested_rate):
        """
        Get corrected interest rate based on credit score
        """
        if credit_score > 50:
            return max(requested_rate, Decimal('0'))
        elif credit_score > 30:
            return max(requested_rate, Decimal('12'))
        elif credit_score > 10:
            return max(requested_rate, Decimal('16'))
        else:
            return requested_rate  # Will be rejected anyway
    
    @staticmethod
    def check_eligibility(customer_id, loan_amount, interest_rate, tenure):
        """
        Check loan eligibility based on credit score and other criteria
        """
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return {
                'approval': False,
                'message': 'Customer not found',
                'interest_rate': interest_rate,
                'corrected_interest_rate': interest_rate,
                'monthly_installment': Decimal('0')
            }
        
        # Calculate credit score
        credit_score = CreditScoreCalculator.calculate_credit_score(customer)
        
        # Get corrected interest rate
        corrected_rate = LoanEligibilityService.get_corrected_interest_rate(
            credit_score, interest_rate
        )
        
        # Calculate monthly installment with corrected rate
        monthly_installment = LoanEligibilityService.calculate_monthly_installment(
            loan_amount, corrected_rate, tenure
        )
        
        # Check basic eligibility based on credit score
        if credit_score <= 10:
            return {
                'approval': False,
                'message': 'Credit score too low for loan approval',
                'interest_rate': interest_rate,
                'corrected_interest_rate': corrected_rate,
                'monthly_installment': Decimal('0')
            }
        
        # Check if sum of all current EMIs > 50% of monthly salary
        current_loans = Loan.objects.filter(
            customer=customer,
            end_date__gte=timezone.now().date()
        )
        
        current_emi_sum = current_loans.aggregate(
            total=Sum('monthly_repayment')
        )['total'] or Decimal('0')
        
        total_emi_with_new_loan = current_emi_sum + monthly_installment
        max_allowed_emi = customer.monthly_salary * Decimal('0.5')
        
        if total_emi_with_new_loan > max_allowed_emi:
            return {
                'approval': False,
                'message': 'Total EMI would exceed 50% of monthly salary',
                'interest_rate': interest_rate,
                'corrected_interest_rate': corrected_rate,
                'monthly_installment': Decimal('0')
            }
        
        # Check interest rate requirements based on credit score
        if credit_score > 50:
            approval = True
            message = 'Loan approved'
        elif credit_score > 30:
            if corrected_rate < 12:
                approval = False
                message = 'Interest rate too low for credit score'
            else:
                approval = True
                message = 'Loan approved with corrected interest rate'
        elif credit_score > 10:
            if corrected_rate < 16:
                approval = False
                message = 'Interest rate too low for credit score'
            else:
                approval = True
                message = 'Loan approved with corrected interest rate'
        else:
            approval = False
            message = 'Credit score too low for loan approval'
        
        return {
            'approval': approval,
            'message': message,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_rate,
            'monthly_installment': monthly_installment if approval else Decimal('0')
        }