from django.contrib import admin
from .models import Customer, Loan


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'customer_id', 'first_name', 'last_name', 
        'phone_number', 'monthly_salary', 'approved_limit', 'current_debt'
    ]
    list_filter = ['approved_limit', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone_number']
    readonly_fields = ['customer_id', 'created_at', 'updated_at']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = [
        'loan_id', 'customer', 'loan_amount', 'tenure', 
        'interest_rate', 'monthly_repayment', 'start_date', 'end_date'
    ]
    list_filter = ['interest_rate', 'tenure', 'start_date']
    search_fields = ['loan_id', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['loan_id', 'created_at', 'updated_at']