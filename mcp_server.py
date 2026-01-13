"""
FastMCP Server for Customer Transaction Services
Using @mcp.tool() decorator pattern
"""
import os, asyncio
import logging
from typing import Optional,List
from dateutil import parser as date_parser
from dotenv import load_dotenv
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from mongo_client import mongo_db

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP('customer-transaction-service')





# ============================================================================
# CUSTOMER TOOLS
# ============================================================================

@mcp.tool()
async def get_customer(customer_id: str) -> str:
    """
    Get customer information by customer ID.
    
    Args:
        customer_id: The unique customer identifier (e.g., 'CUST2001')
    
    Returns:
        Customer information as JSON string
    """
    try:
        customer = await mongo_db.get_customer_by_id(customer_id)
        
        if customer:
            return f"Customer found: {customer}"
        return f"Customer {customer_id} not found"
    except Exception as e:
        logger.error(f"Error in get_customer: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
async def get_transactions_by_filters(customer_id:str, filters: dict) -> str:
    """
    Retrieve transactions based on filters.
    
    Args:
        customer_id (str): The unique identifier of the customer whose accounts are being retrieved.
        filters (dict): Dictionary with transaction fields and filter values.
                        Example: {"customer_id": "CUST2001", "status": "completed"}
    
    Returns:
        list: List of transaction documents matching the filters.
    
    Raises:
        ValueError: If any filter key is not a valid transaction field.
        Exception: If MongoDB query fails.
    
    """
    try:
        
        cursor = await mongo_db.get_transactions_by_filters(customer_id, filters)
        results = []
        async for doc in cursor:
            results.append(doc)
        
        if results:
            return f"Filtered transactions: {results}"
        return "No transactions found matching the given filters."
    
    except Exception as e:
        logger.error(f"Error in get_transactions_by_filters: {e}")
        return f"Error: {str(e)}"


# ============================================================================
# ACCOUNT TOOLS
# ============================================================================

@mcp.tool()
async def get_account(account_id: str) -> str:
    """
    Get account information by account ID.
    
    Args:
        account_id: The unique account identifier (e.g., 'ACC3001')
    
    Returns:
        Account information as JSON string
    """
    try:
        account = await mongo_db.get_account_by_id(account_id)
        
        if account:
            return f"Account found: {account}"
        return f"Account {account_id} not found"
    except Exception as e:
        logger.error(f"Error in get_account: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
async def get_customer_accounts(customer_id: str) -> str:
    """
    Get all accounts belonging to a customer.
    
    Args:
        customer_id: The unique customer identifier (e.g., 'CUST2001')
    
    Returns:
        List of customer accounts with total balance
    """
    try:
        accounts = await mongo_db.get_accounts_by_customer(customer_id)
        
        total_balance = sum(acc.get('balance', 0) for acc in accounts)
        
        result = {
            "customer_id": customer_id,
            "account_count": len(accounts),
            "total_balance": total_balance,
            "accounts": accounts
        }
        
        return f"Customer {customer_id} has {len(accounts)} account(s) with total balance {total_balance}: {result}"
    except Exception as e:
        logger.error(f"Error in get_customer_accounts: {e}")
        return f"Error: {str(e)}"


# ============================================================================
# TRANSACTION TOOLS
# ============================================================================

@mcp.tool()
async def get_transactions_by_customer(customer_id: str) -> str:
    """
    Get all transactions for a specific account by account ID.
    
    Args:
        customer_id (str): The unique identifier of the customer whose accounts are being retrieved.

    Returns:
        Transactions information as JSON string
    """
    try:
        # Assuming mongo_db has a method to get transactions by customer_id
        transactions = await mongo_db.get_transactions_by_customer(customer_id)
        
        if transactions:
            return f"Transactions for customer {customer_id}: {transactions}"
        return f"No transactions found for customer {customer_id}"
    except Exception as e:
        logger.error(f"Error in get_transactions_by_account: {e}")
        return f"Error: {str(e)}"



async def get_accounts_by_filters(customer_id: str, filters: dict) -> List[dict]:
    """
    Retrieve accounts based on filters.

    Args:
        customer_id (str): The unique identifier of the customer whose accounts are being retrieved.
        filters (dict): Dictionary with account fields and values to filter by.

    Returns:
        list: List of account documents matching the filters.

    Raises:
        ValueError: If any filter key is invalid.
        Exception: If MongoDB query fails.
    """
    try:
        
        cursor = await mongo_db.get_accounts_by_filters(customer_id, filters)
        results = []
        async for doc in cursor:
            results.append(doc)
        
        if results:
            return f"Filtered accounts: {results}"
        return "No accounts found matching the given filters."
        
    except Exception as e:
        logger.error(f"Error in get_accounts_by_filters: {e}")
        return f"Error: {str(e)}"
    

@mcp.tool()
async def get_customers_by_filters(filters: dict) -> str:
    """
    Retrieve customers based on filters.

    Args:
        filters (dict): Dictionary with customer fields and values to filter by.

    Returns:
        list: List of customer documents matching the filters.

    Raises:
        ValueError: If any filter key is invalid.
        Exception: If MongoDB query fails.
    """

    try:
        
        cursor = await mongo_db.get_customers_by_filters(filters)
        results = []
        async for doc in cursor:
            results.append(doc)
        
        if results:
            return f"Filtered customers: {results}"
        return "No customers found matching the given filters."
    
    except Exception as e:
        logger.error(f"Error in get_customers_by_filters: {e}")
        return f"Error: {str(e)}"


















@mcp.tool()
async def get_customer_transactions_with_date_time(
    customer_id: str,
    limit: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    
    """
    Get transactions for an account filtered by optional date range and time range.

    Args:
        customer_id: Customer ID to filter transactions
        limit: Maximum number of transactions to return
        start_date: Start date as string "YYYY-MM-DD" (inclusive)
        end_date: End date as string "YYYY-MM-DD" (inclusive)
        start_time: Start time as string "HH:MM:SS" (inclusive)
        end_time: End time as string "HH:MM:SS" (inclusive)

    Returns:
        List of transaction dictionaries matching the filters
    """
    
    try:

        
        transactions = await mongo_db.get_customer_transactions_with_date_time(
            customer_id=customer_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            start_time = start_time,
            end_time = end_time

        )
        
        total_amount = sum(txn.get('amount', 0) for txn in transactions)
        
        result = {
            "customer_id": customer_id,
            "transaction_count": len(transactions),
            "total_amount": total_amount,
            "transactions": transactions
        }
        
        return f"Found {len(transactions)} transactions for account {customer_id} with total amount {total_amount}: {result}"
    except Exception as e:
        logger.error(f"Error in get_account_transactions: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
async def get_all_transactions_summary_for_customer(
    customer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    """
    Aggregate transaction summary by transaction_type for a specific customer.

    This function calculates the total amount, count, and average amount
    of transactions grouped by transaction_type. Optional filters for 
    date and time ranges can be applied.

    Args:
        customer_id: Customer ID to filter transactions
        start_date (str, optional): Start date in 'YYYY-MM-DD' format (inclusive).
        end_date (str, optional): End date in 'YYYY-MM-DD' format (inclusive).
        start_time (str, optional): Start time in 'HH:MM:SS' format (inclusive).
        end_time (str, optional): End time in 'HH:MM:SS' format (inclusive).

    Returns:
        Dict[str, Any]: {
            "customer_id": str,
            "summary_by_type": List[{
                "_id": str,             # transaction_type
                "total_amount": float,
                "count": int,
                "avg_amount": float
            }]
        }
        Returns {"error": str} if an exception occurs.
    """
    try:

        
        summary = await mongo_db.aggregate_transactions_summary_for_customer(
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            start_time = start_time,
            end_time = end_time

        )

        return f"Transaction summary for account {customer_id}: {summary}"
    except Exception as e:
        logger.error(f"Error in get_transaction_summary: {e}")
        return f"Error: {str(e)}"


# ============================================================================
# CALCULATION TOOLS (Sync functions work with async)
# ============================================================================

@mcp.tool()
async def get_current_date_time():
    """
    Returns the current date and time as separate strings.
    
    Returns:
        tuple: (current_date, current_time)
            current_date -> str in 'YYYY-MM-DD'
            current_time -> str in 'HH:MM:SS'
    """
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    return current_date, current_time


@mcp.tool()
async def add(a: float, b: float) -> str:
    """
    Add two numbers together.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        Sum of a and b
    """
    try:
        result = float(a + b)
        return f"{a} + {b} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def subtract(a: float, b: float) -> str:
    """
    Subtract b from a.
    
    Args:
        a: Number to subtract from (minuend)
        b: Number to subtract (subtrahend)
    
    Returns:
        Difference of a and b
    """
    try:
        result = float(a - b)
        return f"{a} - {b} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def multiply(a: float, b: float) -> str:
    """
    Multiply two numbers together.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        Product of a and b
    """
    try:
        result = float(a * b)
        return f"{a} × {b} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def divide(a: float, b: float) -> str:
    """
    Divide a by b.
    
    Args:
        a: Dividend
        b: Divisor (cannot be zero)
    
    Returns:
        Quotient of a and b
    """
    try:
        if b == 0:
            return "Error: Division by zero is not allowed"
        
        result = float(a / b)
        return f"{a} ÷ {b} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"
    
@mcp.tool()
async def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.
    Supports: +, -, *, /, **, %, parentheses
    
    Args:
        expression: Mathematical expression (e.g., "(5000 * 0.03) / 12", "150 + 200 + 300")
    
    Returns:
        Result of the calculation
    """
    try:
        allowed_chars = set('0123456789+-*/().%** ')
        if not all(c in allowed_chars for c in expression):
            return "Error: Expression contains invalid characters"
        
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def sum_numbers(numbers: list[float]) -> str:
    """
    Calculate the sum of multiple numbers.
    
    Args:
        numbers: List of numbers to sum
    
    Returns:
        Total sum
    """
    try:
        result = sum(numbers)
        return f"Sum of {len(numbers)} numbers = {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def average(numbers: list[float]) -> str:
    """
    Calculate the average of multiple numbers.
    
    Args:
        numbers: List of numbers
    
    Returns:
        Average value
    """
    try:
        if not numbers:
            return "Error: Cannot calculate average of empty list"
        result = sum(numbers) / len(numbers)
        return f"Average of {len(numbers)} numbers = {result}"
    except Exception as e:
        return f"Error: {str(e)}"
    



if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Customer Transaction Service")
    logger.info("=" * 60)

    mcp.run(transport="sse")
  


