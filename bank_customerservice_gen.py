from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")


if "banking_db" in client.list_database_names():
    client.drop_database("banking_db")


db = client["banking_db"]


customers_col = db["customers"]
accounts_col = db["accounts"]
transactions_col = db["transactions"]
bank_products_col = db["bank_products"]
# --------------------
# Customers (Egyptian Names)
# --------------------
customers = [
    {
        "id": "CUST2001",
        "full_name": "Ahmed Hassan",
        "date_of_birth": "1989-02-15",
        "email": "ahmed.hassan@email.com",
        "phone_number": "+20-100-123-4567",
        "address": {
            "street": "12 Tahrir Street",
            "city": "Cairo",
            "country": "Egypt"
        },
        "customer_since": "2018-05-10",
        "kyc_status": "Verified"
    },
    {
        "id": "CUST2002",
        "full_name": "Mona El-Sayed",
        "date_of_birth": "1994-07-22",
        "email": "mona.elsayed@email.com",
        "phone_number": "+20-111-987-6543",
        "address": {
            "street": "45 Corniche Road",
            "city": "Alexandria",
            "country": "Egypt"
        },
        "customer_since": "2020-09-18",
        "kyc_status": "Verified"
    }
]

# --------------------
# Accounts
# --------------------
accounts = [
    {
        "id": "ACC3001",
        "customer_id": "CUST2001",
        "account_type": "Savings",
        "currency": "EGP",
        "balance": 85000.75,
        "account_status": "Active",
        "opened_date": "2018-05-10"
    },
    {
        "id": "ACC3002",
        "customer_id": "CUST2001",
        "account_type": "Credit",
        "currency": "EGP",
        "balance": -12000.00,
        "credit_limit": 50000,
        "account_status": "Active",
        "opened_date": "2021-03-01"
    },
    {
        "id": "ACC3003",
        "customer_id": "CUST2002",
        "account_type": "Current",
        "currency": "EGP",
        "balance": 43000.00,
        "account_status": "Active",
        "opened_date": "2020-09-18"
    }
]

# --------------------
# Transactions
# --------------------
transactions = [
    {
        "id": "TXN4001",
        "account_id": "ACC3001",
        "transaction_date": datetime(2025, 1, 3, 11, 30),
        "transaction_type": "Debit",
        "amount": 950.00,
        "merchant_name": "Carrefour Egypt",
        "merchant_category": "Groceries",
        "channel": "POS",
        "transaction_status": "Completed"
    },
    {
        "id": "TXN4002",
        "account_id": "ACC3001",
        "transaction_date": datetime(2025, 1, 5, 18, 15),
        "transaction_type": "Debit",
        "amount": 120.00,
        "merchant_name": "Uber Cairo",
        "merchant_category": "Transport",
        "channel": "Mobile App",
        "transaction_status": "Completed"
    },
      {
    "id": "TXN4006",
    "account_id": "ACC3001",
    "transaction_date": datetime(2025, 1, 5, 14, 45),
    "transaction_type": "Debit",
    "amount": 320.50,
    "merchant_name": "Carrefour Egypt",
    "merchant_category": "Groceries",
    "channel": "POS",
    "transaction_status": "Completed"
},
    {
        "id": "TXN4003",
        "account_id": "ACC3002",
        "transaction_date": datetime(2025, 1, 7, 13, 45),
        "transaction_type": "Debit",
        "amount": 7800.00,
        "merchant_name": "Samsung Store Egypt",
        "merchant_category": "Electronics",
        "channel": "POS",
        "transaction_status": "Completed"
    },
      {
        "id": "TXN4004",
        "account_id": "ACC3002",
        "transaction_date": datetime(2025, 1, 7, 16, 20),
        "transaction_type": "Credit",
        "amount": 2500.00,
        "merchant_name": "Salary Deposit",
        "merchant_category": "Income",
        "channel": "Bank Transfer",
        "transaction_status": "Completed"
    },
    {
        "id": "TXN4004",
        "account_id": "ACC3003",
        "transaction_date": datetime(2025, 1, 8,),
        "transaction_type": "Credit",
        "amount": 15000.00,
        "merchant_name": "Salary Deposit",
        "merchant_category": "Payroll",
        "channel": "Bank Transfer",
        "transaction_status": "Completed"
    }
]
for txn in transactions:
    dt = txn["transaction_date"]
    txn["transaction_date"] = dt.strftime("%Y-%m-%d")
    txn["transaction_time"] = dt.strftime("%H:%M:%S")


bank_products = [
  {
    "product_id": "PROD1001",
    "product_name": "Ahly Savings Account",
    "category": "Deposit",
    "features": [
      "3.5% annual interest",
      "No minimum balance requirement",
      "Free debit card",
      "Mobile and online banking access"
    ],
    "eligibility": "Individuals above 18 years with valid ID",
    "fees": [
      "No maintenance fee",
      "Penalty of 50 EGP if account dormant for 12 months"
    ],
    "status": "Active",
    "interest_rate": 3.5,
    "faqs": [
      {
        "question": "What is the minimum balance for Ahly Savings Account?",
        "answer": "There is no minimum balance requirement."
      },
      {
        "question": "Can I access the account online?",
        "answer": "Yes, the account supports full mobile and internet banking."
      }
    ]
  },
  {
    "product_id": "PROD1002",
    "product_name": "Cairo Current Account",
    "category": "Deposit",
    "features": [
      "Unlimited transactions",
      "Overdraft facility up to 20,000 EGP",
      "Checkbook available on request"
    ],
    "eligibility": "Business entities and individual professionals",
    "fees": [
      "Monthly maintenance fee: 100 EGP",
      "Checkbook issuance fee: 25 EGP per booklet"
    ],
    "status": "Active",
    "interest_rate": 0,
    "faqs": [
      {
        "question": "Is there an interest on Cairo Current Account?",
        "answer": "No, current accounts do not earn interest."
      }
    ]
  },
  {
    "product_id": "PROD1003",
    "product_name": "Nile Personal Loan",
    "category": "Loan",
    "features": [
      "Loan amount up to 200,000 EGP",
      "Flexible repayment up to 5 years",
      "Unsecured loan with fixed EMI"
    ],
    "eligibility": "Salaried or self-employed individuals with minimum income 5,000 EGP/month",
    "fees": [
      "Processing fee: 1% of loan amount",
      "Early repayment allowed without penalty"
    ],
    "status": "Active",
    "interest_rate": 12,
    "faqs": [
      {
        "question": "Can I prepay my personal loan?",
        "answer": "Yes, early repayment is allowed without any penalty."
      }
    ]
  },
  {
    "product_id": "PROD1004",
    "product_name": "Pharaoh Credit Card",
    "category": "Credit",
    "features": [
      "Credit limit up to 50,000 EGP",
      "Cashback 1% on all purchases",
      "Reward points on online shopping",
      "Free travel insurance"
    ],
    "eligibility": "Individuals above 21 years with stable income",
    "fees": [
      "Annual fee: 500 EGP",
      "Late payment fee: 200 EGP"
    ],
    "status": "Active",
    "interest_rate": 32,
    "faqs": [
      {
        "question": "What is the annual fee for Pharaoh Credit Card?",
        "answer": "The annual fee is 500 EGP."
      },
      {
        "question": "Does the card offer reward points?",
        "answer": "Yes, reward points are earned on all online shopping transactions."
      }
    ]
  },
  {
    "product_id": "PROD1005",
    "product_name": "Delta Fixed Deposit",
    "category": "Deposit",
    "features": [
      "Higher interest: 6% per annum",
      "Term options: 6, 12, 24 months",
      "Penalty for early withdrawal applies"
    ],
    "eligibility": "Individuals and corporate entities",
    "fees": [
      "Early withdrawal penalty: 1% of principal"
    ],
    "status": "Active",
    "interest_rate": 6,
    "faqs": [
      {
        "question": "What happens if I withdraw early from Delta Fixed Deposit?",
        "answer": "A penalty of 1% of the principal will be applied."
      }
    ]
  }
]

# --------------------
# Insert Data
# --------------------
customers_col.insert_many(customers)
accounts_col.insert_many(accounts)
transactions_col.insert_many(transactions)
bank_products_col.insert_many(bank_products)

print("✅ Egyptian mock banking data inserted successfully!")
