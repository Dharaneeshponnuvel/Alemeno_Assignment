from celery import shared_task
import pandas as pd
import os
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from .models import Customer, Loan


@shared_task
def ingest_customer_data():
    """
    Background task to ingest customer data from Excel file
    """
    try:
        file_path = os.path.join(settings.DATA_FILES_PATH, 'customer_data.xlsx')
        
        if not os.path.exists(file_path):
            return {'status': 'error', 'message': 'Customer data file not found'}
        
        df = pd.read_excel(file_path)
        
        customers_created = 0
        customers_updated = 0
        
        for _, row in df.iterrows():
            try:
                # Calculate approved limit (rounded to nearest lakh)
                approved_limit = (Decimal(str(row['approved_limit'])) / 100000).quantize(
                    Decimal('1'), rounding=ROUND_HALF_UP
                ) * 100000
                
                customer, created = Customer.objects.update_or_create(
                    customer_id=row['customer_id'],
                    defaults={
                        'first_name': row['first_name'],
                        'last_name': row['last_name'],
                        'phone_number': row['phone_number'],
                        'monthly_salary': Decimal(str(row['monthly_salary'])),
                        'approved_limit': approved_limit,
                        'current_debt': Decimal(str(row.get('current_debt', 0))),
                        'age': row.get('age', 30)  # Default age if not provided
                    }
                )
                
                if created:
                    customers_created += 1
                else:
                    customers_updated += 1
                    
            except Exception as e:
                print(f"Error processing customer {row.get('customer_id', 'unknown')}: {e}")
                continue
        
        return {
            'status': 'success',
            'customers_created': customers_created,
            'customers_updated': customers_updated
        }
        
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@shared_task
def ingest_loan_data():
    """
    Background task to ingest loan data from Excel file
    """
    try:
        file_path = os.path.join(settings.DATA_FILES_PATH, 'loan_data.xlsx')
        
        if not os.path.exists(file_path):
            return {'status': 'error', 'message': 'Loan data file not found'}
        
        df = pd.read_excel(file_path)
        
        loans_created = 0
        loans_updated = 0
        
        for _, row in df.iterrows():
            try:
                # Get customer
                try:
                    customer = Customer.objects.get(customer_id=row['customer id'])
                except Customer.DoesNotExist:
                    print(f"Customer {row['customer id']} not found for loan {row['loan id']}")
                    continue
                
                # Parse dates
                start_date = pd.to_datetime(row['start date']).date()
                end_date = pd.to_datetime(row['end date']).date()
                
                loan, created = Loan.objects.update_or_create(
                    loan_id=row['loan id'],
                    defaults={
                        'customer': customer,
                        'loan_amount': Decimal(str(row['loan amount'])),
                        'tenure': int(row['tenure']),
                        'interest_rate': Decimal(str(row['interest rate'])),
                        'monthly_repayment': Decimal(str(row['monthly repayment (emi)'])),
                        'emis_paid_on_time': int(row['EMIs paid on time']),
                        'start_date': start_date,
                        'end_date': end_date
                    }
                )
                
                if created:
                    loans_created += 1
                else:
                    loans_updated += 1
                    
            except Exception as e:
                print(f"Error processing loan {row.get('loan id', 'unknown')}: {e}")
                continue
        
        return {
            'status': 'success',
            'loans_created': loans_created,
            'loans_updated': loans_updated
        }
        
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@shared_task
def ingest_all_data():
    """
    Background task to ingest both customer and loan data
    """
    customer_result = ingest_customer_data()
    loan_result = ingest_loan_data()
    
    return {
        'customer_ingestion': customer_result,
        'loan_ingestion': loan_result
    }