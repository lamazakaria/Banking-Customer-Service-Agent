from typing import List, Dict, Any, Optional
from pymongo import AsyncMongoClient
from datetime import datetime
import logging
from config import MongoConfig
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)

# List of allowed keys in the transaction collection based on your schema
ALLOWED_TRANSACTION_FIELDS = {
    "id", "account_id", "transaction_type", "amount", "currency",
    "description", "merchant", "category", "status",
    "transaction_date", "transaction_time", "balance_after",
    "reference_number", "created_at"
}
ALLOWED_CUSTOMER_FIELDS = {
    "id", "first_name", "last_name", "email", "phone", "date_of_birth", 
    "customer_since", "kyc_status", "created_at", "updated_at",
    "address", "address.street", "address.city", "address.state", 
    "address.postal_code", "address.country"
}

ALLOWED_ACCOUNT_FIELDS = {
    "id", "customer_id", "account_type", "account_number", "balance", 
    "currency", "status", "opened_date", "interest_rate", "created_at", "updated_at"
}


class AsyncMongoDBClient:
    """Async MongoDB client for read-only operations"""
    
    def __init__(self):
        self.client = AsyncMongoClient()
        self.uri = MongoConfig.MONGO_URI
        self.database_name = MongoConfig.DATABASE_NAME
        self.db = None
        self._is_connected = False
    
    async def _ensure_connected(self):
        """Ensure we're connected - creates client in current event loop if needed"""
        if not self._is_connected or self.client is None:
            await self.connect()
    

    
    async def connect(self):
        """Establish async connection to MongoDB"""
        if self._is_connected and self.client is not None:
            logger.info("MongoDB already connected")
            return

        try:
    
            await self.client.aconnect()
            # Test the connection
            await self.client.server_info()
            self.db = self.client[self.database_name]
            logger.info(f"✓ Connected to MongoDB: {self.database_name}")
            self._is_connected = True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
            self._is_connected = False
            raise
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            await self.client.close()
            logger.info("✓ Disconnected from MongoDB")
    
    # ========================================================================
    # CUSTOMER OPERATIONS (READ-ONLY)
    # ========================================================================
    
    async def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve customer by ID"""
        await self._ensure_connected()
        try:
            customer = await self.db.customers.find_one(
                {"id": customer_id},
                {"_id": 0}  # Exclude the _id field
            )
            return customer
        except Exception as e:
            logger.error(f"Error fetching customer {customer_id}: {e}")
            return f"Error: {str(e)}"
    
    async def search_customers(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search customers with filters"""
        await self._ensure_connected()
        try:
            query = filters or {}
            cursor = self.db.customers.find(query).limit(limit)
            customers = await cursor.to_list()
            
            for customer in customers:
                customer['_id'] = str(customer['_id'])
            
            return customers
        except Exception as e:
            logger.error(f"Error searching customers: {e}")
            return []
    
    # ========================================================================
    # ACCOUNT OPERATIONS (READ-ONLY)
    # ========================================================================
    
    async def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve account by ID"""
        await self._ensure_connected()
        try:
            account = await self.db.accounts.find_one({"id": account_id}, {"_id": 0})

            return account
        except Exception as e:
            logger.error(f"Error fetching account {account_id}: {e}")
            return f"Error: {str(e)}"
    
    async def get_accounts_by_customer(
        self, 
        customer_id: str
    ) -> List[Dict[str, Any]]:
        """Get all accounts for a customer"""
        await self._ensure_connected()
        try:
            cursor = self.db.accounts.find({"customer_id": customer_id},{"_id": 0}).limit(100)
            accounts = await cursor.to_list(length=100)
            print(f"Fetched {len(accounts)} accounts for customer {customer_id}")
            
            return accounts
        except Exception as e:
            logger.error(f"Error fetching accounts for {customer_id}: {e}")
            return []
        
    
    # ========================================================================
    # TRANSACTION OPERATIONS (READ-ONLY)
    # ========================================================================


    async def get_transactions_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """
        Get all transactions for a customer's accounts, sorted by most recent.
        """
        await self._ensure_connected()
        
        try:
            pipeline = [
                # Match accounts of the customer
                {"$match": {"customer_id": customer_id}},
                
                # Lookup transactions for each account
                {
                    "$lookup": {
                        "from": "transactions",
                        "localField": "id",       # account id
                        "foreignField": "account_id",
                        "as": "transactions"
                    }
                },
                
                # Unwind transactions so each transaction is a separate document
                {"$unwind": "$transactions"},
                
                # Replace root with transaction document
                {"$replaceRoot": {"newRoot": "$transactions"}},
                
                # Sort by transaction_date descending (most recent first)
                {"$sort": {"transaction_date": DESCENDING}}
            ]

            cursor = await self.db.accounts.aggregate(pipeline)
            transactions = [doc async for doc in cursor]
            print(f"Fetched {len(transactions)} transactions for customer {customer_id}")
            return f"All transactions for customer {customer_id}: {transactions}"

        except Exception as e:
            logger.error(f"Error fetching transactions for {customer_id}: {e}")
            return []
        

    async def get_transactions_by_account_id(
        self, 
        account_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all transactions for a specific account, sorted by date and time descending.

        Args:
            account_id (str): Account ID to fetch transactions for.
            limit (int, optional): Maximum number of transactions to return. Default is 50.

        Returns:
            List[Dict[str, Any]]: List of transactions, each as a dict, with _id excluded.
        """
        await self._ensure_connected()
        try:
            cursor = self.db.transactions.find(
                {"account_id": account_id},
                {"_id": 0}  # exclude MongoDB _id
            ).sort([
                ("transaction_date", -1),  # sort by date descending
                ("transaction_time", -1)   # sort by time descending
            ]).limit(limit)

            transactions = []
            async for txn in cursor:
                transactions.append(txn)

            return transactions

        except Exception as e:
            logger.error(f"Error fetching transactions for account {account_id}: {e}")
            return []

    async def get_customer_transactions_with_date_time(
        self,
        customer_id: str,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for an account filtered by optional date range and time range.

        Args:
            customer_id (str): The unique identifier of the customer whose accounts are being retrieved.
            limit: Maximum number of transactions to return
            start_date: Start date as string "YYYY-MM-DD" (inclusive)
            end_date: End date as string "YYYY-MM-DD" (inclusive)
            start_time: Start time as string "HH:MM:SS" (inclusive)
            end_time: End time as string "HH:MM:SS" (inclusive)

        Returns:
            List of transaction dictionaries matching the filters
        """
        await self._ensure_connected()
        try:
            # Build transaction filters
            transaction_filter = {}
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                transaction_filter["transactions.transaction_date"] = date_filter

            if start_time or end_time:
                time_filter = {}
                if start_time:
                    time_filter["$gte"] = start_time
                if end_time:
                    time_filter["$lte"] = end_time
                transaction_filter["transactions.transaction_time"] = time_filter

            # Aggregation pipeline
            pipeline = [
                # Step 1: Match accounts for the customer
                {"$match": {"customer_id": customer_id}},

                # Step 2: Lookup transactions for each account
                {
                    "$lookup": {
                        "from": "transactions",
                        "localField": "id",       # account id
                        "foreignField": "account_id",
                        "as": "transactions"
                    }
                },

                # Step 3: Unwind transactions
                {"$unwind": "$transactions"},

                # Step 4: Apply optional date/time filters
                {"$match": transaction_filter} if transaction_filter else {},

                # Step 5: Replace root to only return transaction documents
                {"$replaceRoot": {"newRoot": "$transactions"}},

                # Step 6: Sort by date/time descending
                {"$sort": {"transaction_date": DESCENDING, "transaction_time": DESCENDING}},

                # Step 7: Limit results
                {"$limit": limit}
            ]

            # Remove empty stages (if no filters)
            pipeline = [stage for stage in pipeline if stage]

            cursor = await self.db.accounts.aggregate(pipeline)
            transactions = [doc async for doc in cursor]


            return transactions
        except Exception as e:
            logger.error(f"Error fetching transactions for {customer_id}: {e}")
            return []

    
    async def aggregate_transactions_summary_for_customer(
        self,
        customer_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get aggregated transaction summary by transaction_type, with optional date and time filters"""
        await self._ensure_connected()
        try:
                # Build transaction filters
            transaction_filter = {}
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                transaction_filter["transactions.transaction_date"] = date_filter

            if start_time or end_time:
                time_filter = {}
                if start_time:
                    time_filter["$gte"] = start_time
                if end_time:
                    time_filter["$lte"] = end_time
                transaction_filter["transactions.transaction_time"] = time_filter

            # Aggregation pipeline
            pipeline = [
                # Step 1: Match accounts for the customer
                {"$match": {"customer_id": customer_id}},

                # Step 2: Lookup transactions for each account
                {
                    "$lookup": {
                        "from": "transactions",
                        "localField": "id",
                        "foreignField": "account_id",
                        "as": "transactions"
                    }
                },

                # Step 3: Flatten transactions
                {"$unwind": "$transactions"},

                # Step 4: Apply optional date/time filters
                {"$match": transaction_filter} if transaction_filter else {},

                # Step 5: Replace root with transaction document
                {"$replaceRoot": {"newRoot": "$transactions"}},

                # Step 6: Group by transaction_type
                {
                    "$group": {
                        "_id": "$transaction_type",
                        "total_amount": {"$sum": "$amount"},
                        "count": {"$sum": 1},
                        "avg_amount": {"$avg": "$amount"}
                    }
                }
            ]

            # Remove empty stages if no filters
            pipeline = [stage for stage in pipeline if stage]

            cursor = await self.db.accounts.aggregate(pipeline)
            summary = [doc async for doc in cursor]

            return {"customer_id": customer_id, "summary_by_type": summary}
        except Exception as e:
            logger.error(f"Error aggregating transactions: {e}")
            return {"error": str(e)}



    async def get_transactions_by_filters(self, customer_id: str, filters: dict) -> str:
        """
        Get transactions based on filters.
        """
        await self._ensure_connected()
        try:
            # Validate filters
            invalid_keys = [k for k in filters if k not in ALLOWED_TRANSACTION_FIELDS]
            if invalid_keys:
                return f"Error: Invalid field(s) in filters: {', '.join(invalid_keys)}"

            # Build aggregation pipeline
            pipeline = [
                # Step 1: Get accounts for the customer
                {"$match": {"customer_id": customer_id}},

                # Step 2: Lookup transactions for each account
                {
                    "$lookup": {
                        "from": "transactions",
                        "localField": "id",      # account id
                        "foreignField": "account_id",
                        "as": "transactions"
                    }
                },

                # Step 3: Flatten transactions
                {"$unwind": "$transactions"},

                # Step 4: Replace root with transaction document
                {"$replaceRoot": {"newRoot": "$transactions"}},
            ]

            # Step 5: Apply filters if provided
            if filters:
                pipeline.append({"$match": filters})

            # Step 6: Sort by most recent
            pipeline.append({"$sort": {"transaction_date": DESCENDING}})

            cursor = await self.db.accounts.aggregate(pipeline)
            transactions = [doc async for doc in cursor]

            return f"Filtered transactions: {transactions}"
            
        except Exception as e:
            logger.error(f"Error in get_transactions_by_filters: {e}")
            return f"Error: {str(e)}"


    async def get_accounts_by_filters(self, customer_id: str, filters: dict) -> str:
        """
        Get accounts based on filters.
        """
        await self._ensure_connected()
        try:
            # Check for invalid filter keys
            invalid_keys = [k for k in filters if k not in ALLOWED_ACCOUNT_FIELDS]
            if invalid_keys:
                return f"Error: Invalid field(s) in filters: {', '.join(invalid_keys)}"

            # Build the aggregation pipeline
            pipeline = [
                # Match the customer_id first
                {"$match": {"customer_id": customer_id}},
                
                # Apply additional filters if any
                {"$match": filters} if filters else {}
            ]

            # Remove empty stages (if no filters)
            pipeline = [stage for stage in pipeline if stage]

            cursor = await self.db.accounts.aggregate(pipeline)
            results = [doc async for doc in cursor]

            if results:
                return f"Filtered accounts: {results}"
            return "No accounts found matching the given filters."
        
        except Exception as e:
            logger.error(f"Error in get_accounts_by_filters: {e}")
            return f"Error: {str(e)}"
        
    async def get_customers_by_filters(self, filters: dict) -> str:
        """
        Get customers based on filters.
        """
        await self._ensure_connected()
        try:
            invalid_keys = [k for k in filters if k not in ALLOWED_CUSTOMER_FIELDS]
            if invalid_keys:
                return f"Error: Invalid field(s) in filters: {', '.join(invalid_keys)}"
            
            cursor = self.db.customers.find(filters,{"_id": 0})
            results = []
            async for doc in cursor:
                results.append(doc)
            
            if results:
                return f"Filtered customers: {results}"
            return "No customers found matching the given filters."
        
        except Exception as e:
            logger.error(f"Error in get_customers_by_filters: {e}")
            return f"Error: {str(e)}"


mongo_db = AsyncMongoDBClient()


if __name__ == "__main__":
    import asyncio

    async def test():
        mongo_client = AsyncMongoDBClient()
        # await mongo_client.connect()
        
        customer = await mongo_client.get_customer_by_id("CUST2001")
        print("Customer:", customer)
        
        accounts = await mongo_client.get_accounts_by_customer("CUST2001")
        print("Accounts:", accounts)
        
        # transactions = await mongo_client.get_transactions_by_account("ACC3001", limit=5)
        # print("Transactions:", transactions)
        
        summary = await mongo_client.aggregate_transaction_summary("ACC3001")
        print("Transaction Summary:", summary)
        
        await mongo_client.disconnect()
    
    asyncio.run(test())

