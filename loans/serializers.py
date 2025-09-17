from rest_framework import serializers
from .models import Customer, Loan
from decimal import Decimal, ROUND_HALF_UP


class CustomerRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(min_value=18, max_value=100)
    monthly_income = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0.01')
    )
    phone_number = serializers.IntegerField()

    def validate_phone_number(self, value):
        if Customer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already exists.")
        return value

    def create(self, validated_data):
        # Calculate approved limit: 36 * monthly_salary, rounded to nearest lakh
        monthly_income = validated_data['monthly_income']
        approved_limit = 36 * monthly_income
        approved_limit = (approved_limit / 100000).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        ) * 100000

        customer = Customer.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            age=validated_data['age'],
            phone_number=validated_data['phone_number'],
            monthly_salary=monthly_income,
            approved_limit=approved_limit
        )
        return customer


class CustomerRegistrationResponseSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    monthly_income = serializers.DecimalField(
        source='monthly_salary', max_digits=10, decimal_places=2
    )

    class Meta:
        model = Customer
        fields = [
            'customer_id', 'name', 'age', 'monthly_income', 
            'approved_limit', 'phone_number'
        ]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class LoanEligibilitySerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01')
    )
    interest_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal('0')
    )
    tenure = serializers.IntegerField(min_value=1, max_value=360)

    def validate_customer_id(self, value):
        if not Customer.objects.filter(customer_id=value).exists():
            raise serializers.ValidationError("Customer does not exist.")
        return value


class LoanEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=12, decimal_places=2)


class CreateLoanSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01')
    )
    interest_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal('0')
    )
    tenure = serializers.IntegerField(min_value=1, max_value=360)

    def validate_customer_id(self, value):
        if not Customer.objects.filter(customer_id=value).exists():
            raise serializers.ValidationError("Customer does not exist.")
        return value


class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True
    )


class CustomerDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='customer_id')

    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'age']


class LoanDetailSerializer(serializers.ModelSerializer):
    customer = CustomerDetailSerializer(read_only=True)
    loan_approved = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'loan_id', 'customer', 'loan_amount', 'interest_rate',
            'monthly_repayment', 'tenure', 'loan_approved'
        ]

    def get_loan_approved(self, obj):
        return True  # All loans in DB are approved


class CustomerLoanListSerializer(serializers.ModelSerializer):
    repayments_left = serializers.IntegerField(read_only=True)
    loan_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    monthly_installment = serializers.DecimalField(
        source='monthly_repayment', max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Loan
        fields = [
            'loan_id', 'loan_amount', 'interest_rate',
            'monthly_installment', 'repayments_left'
        ]