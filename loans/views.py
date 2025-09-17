from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import Customer, Loan
from .serializers import (
    CustomerRegistrationSerializer,
    CustomerRegistrationResponseSerializer,
    LoanEligibilitySerializer,
    LoanEligibilityResponseSerializer,
    CreateLoanSerializer,
    CreateLoanResponseSerializer,
    LoanDetailSerializer,
    CustomerLoanListSerializer
)
from .services import LoanEligibilityService
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


@swagger_auto_schema(
    method='post',
    request_body=CustomerRegistrationSerializer,
    responses={201: CustomerRegistrationResponseSerializer}
)
@api_view(['POST'])
def register_customer(request):
    """
    Register a new customer with approved limit based on salary
    approved_limit = 36 * monthly_salary (rounded to nearest lakh)
    """
    serializer = CustomerRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        customer = serializer.save()
        response_serializer = CustomerRegistrationResponseSerializer(customer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=LoanEligibilitySerializer,
    responses={200: LoanEligibilityResponseSerializer}
)
@api_view(['POST'])
def check_eligibility(request):
    """
    Check loan eligibility based on credit score and other criteria
    """
    serializer = LoanEligibilitySerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        
        result = LoanEligibilityService.check_eligibility(
            customer_id=data['customer_id'],
            loan_amount=data['loan_amount'],
            interest_rate=data['interest_rate'],
            tenure=data['tenure']
        )
        
        response_data = {
            'customer_id': data['customer_id'],
            'approval': result['approval'],
            'interest_rate': result['interest_rate'],
            'corrected_interest_rate': result['corrected_interest_rate'],
            'tenure': data['tenure'],
            'monthly_installment': result['monthly_installment']
        }
        
        response_serializer = LoanEligibilityResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=CreateLoanSerializer,
    responses={201: CreateLoanResponseSerializer}
)
@api_view(['POST'])
def create_loan(request):
    """
    Process a new loan based on eligibility
    """
    serializer = CreateLoanSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        
        # Check eligibility first
        result = LoanEligibilityService.check_eligibility(
            customer_id=data['customer_id'],
            loan_amount=data['loan_amount'],
            interest_rate=data['interest_rate'],
            tenure=data['tenure']
        )
        
        if not result['approval']:
            response_data = {
                'loan_id': None,
                'customer_id': data['customer_id'],
                'loan_approved': False,
                'message': result['message'],
                'monthly_installment': None
            }
            response_serializer = CreateLoanResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        # Create the loan
        try:
            customer = Customer.objects.get(customer_id=data['customer_id'])
            
            # Calculate dates
            start_date = timezone.now().date()
            end_date = start_date + relativedelta(months=data['tenure'])
            
            loan = Loan.objects.create(
                customer=customer,
                loan_amount=data['loan_amount'],
                tenure=data['tenure'],
                interest_rate=result['corrected_interest_rate'],
                monthly_repayment=result['monthly_installment'],
                start_date=start_date,
                end_date=end_date
            )
            
            # Update customer's current debt
            customer.current_debt += data['loan_amount']
            customer.save()
            
            response_data = {
                'loan_id': loan.loan_id,
                'customer_id': data['customer_id'],
                'loan_approved': True,
                'message': 'Loan approved successfully',
                'monthly_installment': result['monthly_installment']
            }
            
            response_serializer = CreateLoanResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Customer.DoesNotExist:
            response_data = {
                'loan_id': None,
                'customer_id': data['customer_id'],
                'loan_approved': False,
                'message': 'Customer not found',
                'monthly_installment': None
            }
            response_serializer = CreateLoanResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    responses={200: LoanDetailSerializer}
)
@api_view(['GET'])
def view_loan(request, loan_id):
    """
    View loan details and customer details
    """
    try:
        loan = get_object_or_404(Loan, loan_id=loan_id)
        serializer = LoanDetailSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Loan.DoesNotExist:
        return Response(
            {'error': 'Loan not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@swagger_auto_schema(
    method='get',
    responses={200: CustomerLoanListSerializer(many=True)}
)
@api_view(['GET'])
def view_customer_loans(request, customer_id):
    """
    View all current loan details by customer id
    """
    try:
        customer = get_object_or_404(Customer, customer_id=customer_id)
        loans = Loan.objects.filter(customer=customer)
        serializer = CustomerLoanListSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )