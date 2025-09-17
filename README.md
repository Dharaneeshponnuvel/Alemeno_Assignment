# Credit Approval System

A Django-based backend system for credit approval with loan eligibility checking based on historical data and credit scoring.

## Features

- Customer registration with automatic credit limit calculation
- Credit score calculation based on historical loan data
- Loan eligibility checking with automatic interest rate correction
- Comprehensive REST API with proper error handling
- Background task processing for data ingestion
- Docker containerization with PostgreSQL and Redis
- Swagger API documentation

## Tech Stack

- **Backend**: Django 4.2 + Django Rest Framework
- **Database**: PostgreSQL
- **Task Queue**: Celery with Redis
- **Containerization**: Docker & Docker Compose
- **Documentation**: Swagger/OpenAPI

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd credit-approval-system
   ```

2. **Prepare data files**:
   - Place `customer_data.xlsx` in the `data/` directory
   - Place `loan_data.xlsx` in the `data/` directory

3. **Start the application**:
   ```bash
   docker-compose up --build
   ```

4. **Access the API**:
   - API Base URL: http://localhost:8000
   - Swagger Documentation: http://localhost:8000/swagger/
   - Admin Panel: http://localhost:8000/admin/

## API Endpoints

### 1. Customer Registration
```
POST /register/
```
Register a new customer with automatic credit limit calculation.

**Request Body**:
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "age": 30,
  "monthly_income": 50000,
  "phone_number": 1234567890
}
```

### 2. Check Loan Eligibility
```
POST /check-eligibility/
```
Check if a customer is eligible for a loan based on their credit score.

**Request Body**:
```json
{
  "customer_id": 1,
  "loan_amount": 100000,
  "interest_rate": 10.5,
  "tenure": 12
}
```

### 3. Create Loan
```
POST /create-loan/
```
Process and create a new loan if the customer is eligible.

### 4. View Loan Details
```
GET /view-loan/{loan_id}/
```
Get detailed information about a specific loan.

### 5. View Customer Loans
```
GET /view-loans/{customer_id}/
```
Get all loans for a specific customer.

## Credit Score Calculation

The system calculates credit scores based on:

1. **Past Loans Paid on Time** (40% weight)
2. **Number of Loans Taken** (20% weight)  
3. **Loan Activity in Current Year** (20% weight)
4. **Loan Approved Volume** (20% weight)

Special rules:
- If current debt > approved limit → Credit Score = 0
- If total EMIs > 50% of salary → Loan rejected

## Interest Rate Rules

- **Credit Score > 50**: Any interest rate accepted
- **Credit Score 30-50**: Minimum 12% interest rate
- **Credit Score 10-30**: Minimum 16% interest rate
- **Credit Score < 10**: No loans approved

## Data Ingestion

The system includes background tasks for ingesting data from Excel files:

```python
# To ingest customer data
from loans.tasks import ingest_customer_data
ingest_customer_data.delay()

# To ingest loan data  
from loans.tasks import ingest_loan_data
ingest_loan_data.delay()

# To ingest all data
from loans.tasks import ingest_all_data
ingest_all_data.delay()
```

## Development

### Running Tests
```bash
docker-compose exec web python manage.py test
```

### Creating Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

### Accessing Database
```bash
docker-compose exec db psql -U postgres -d credit_approval
```

## Project Structure

```
credit-approval-system/
├── credit_approval/          # Django project settings
├── loans/                    # Main application
│   ├── models.py            # Database models
│   ├── views.py             # API endpoints
│   ├── serializers.py       # Data serialization
│   ├── services.py          # Business logic
│   ├── tasks.py             # Background tasks
│   └── tests.py             # Unit tests
├── data/                     # Excel data files
├── docker-compose.yml       # Container orchestration
├── Dockerfile              # Application container
└── requirements.txt        # Python dependencies
```

## Key Features

- **Automatic Credit Limit**: Calculated as 36 × monthly_salary (rounded to nearest lakh)
- **Compound Interest EMI**: Uses proper compound interest formula
- **Smart Interest Rate Correction**: Automatically adjusts rates based on credit score
- **Comprehensive Error Handling**: Proper HTTP status codes and error messages
- **Background Data Processing**: Asynchronous Excel file ingestion
- **Production Ready**: Dockerized with proper logging and monitoring

## Contributing

1. Follow Django best practices
2. Maintain test coverage
3. Use proper error handling
4. Document API changes
5. Follow PEP 8 style guidelines

## License

This project is created for internship assignment purposes.