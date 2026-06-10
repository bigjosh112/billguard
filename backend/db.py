"""
MongoDB Atlas client for BillGuard.
All financial data lives here — transactions, bills, salary, forecasts.
The agent queries this via MCP at every reasoning step.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from bson.errors import InvalidId


MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "billguard"


class MongoDBClient:
    def __init__(self):
        self.client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=10_000,
            connectTimeoutMS=10_000,
            socketTimeoutMS=30_000,
        )
        self.db = self.client[DB_NAME]
        self.transactions = self.db["transactions"]
        self.bills = self.db["bills"]
        self.salary = self.db["salary"]
        self.forecasts = self.db["forecasts"]
        self.sessions = self.db["sessions"]

    async def ping(self) -> bool:
        await self.client.admin.command("ping")
        return True

    async def create_indexes(self):
        await self.transactions.create_index([("session_id", 1), ("date", -1)])
        await self.transactions.create_index([("session_id", 1), ("category", 1)])
        await self.transactions.create_index([("session_id", 1), ("reference", 1)])
        await self.bills.create_index([("session_id", 1), ("due_date", 1)])
        await self.salary.create_index([("session_id", 1), ("active", 1)])
        await self.sessions.create_index([("session_id", 1), ("timestamp", -1)])

    async def store_transactions(self, transactions: list, session_id: str) -> int:
        """Store parsed bank transactions. Deduplicates by reference within session."""
        if not transactions:
            return 0

        stored = 0
        for txn in transactions:
            txn["session_id"] = session_id
            existing = await self.transactions.find_one({
                "reference": txn.get("reference"),
                "session_id": session_id,
            })
            if not existing:
                txn["created_at"] = datetime.utcnow()
                await self.transactions.insert_one(txn)
                stored += 1

        return stored

    async def get_transactions(
        self,
        limit: int = 100,
        category: Optional[str] = None,
        session_id: str = "default",
    ) -> list:
        """Get transactions, newest first."""
        query: dict = {"session_id": session_id}
        if category:
            query["category"] = category

        cursor = self.transactions.find(query).sort("date", -1).limit(limit)
        txns = await cursor.to_list(length=limit)

        for t in txns:
            t["_id"] = str(t["_id"])

        return txns

    async def store_bill(self, bill: dict, session_id: str) -> str:
        """Store an upcoming bill. Skips duplicate name+amount for this session."""
        existing = await self.bills.find_one({
            "session_id": session_id,
            "name": bill.get("name"),
            "amount": bill.get("amount"),
            "paid": False,
        })
        if existing:
            return str(existing["_id"])

        bill["session_id"] = session_id
        bill["created_at"] = datetime.utcnow()
        bill["paid"] = False
        result = await self.bills.insert_one(bill)
        return str(result.inserted_id)

    async def get_bills(self, include_paid: bool = False, session_id: str = "default") -> list:
        """Get upcoming bills, sorted by due date."""
        query: dict = {"session_id": session_id}
        if not include_paid:
            query["paid"] = False
        cursor = self.bills.find(query).sort("due_date", 1)
        bills = await cursor.to_list(length=100)
        for b in bills:
            b["_id"] = str(b["_id"])
        return bills

    async def delete_bill(self, bill_id: str, session_id: str = "default"):
        try:
            await self.bills.delete_one({
                "_id": ObjectId(bill_id),
                "session_id": session_id,
            })
        except InvalidId:
            pass

    async def mark_bill_paid(self, bill_id: str, session_id: str = "default"):
        try:
            await self.bills.update_one(
                {
                    "_id": ObjectId(bill_id),
                    "session_id": session_id,
                },
                {"$set": {
                    "paid": True,
                    "paid_at": datetime.utcnow(),
                }},
            )
        except InvalidId:
            pass

    async def store_salary(self, salary: dict, session_id: str) -> str:
        """Store salary info. Only one active record per session at a time."""
        salary["session_id"] = session_id
        salary["created_at"] = datetime.utcnow()
        salary["active"] = True
        await self.salary.update_many(
            {"session_id": session_id},
            {"$set": {"active": False}},
        )
        result = await self.salary.insert_one(salary)
        return str(result.inserted_id)

    async def get_salary(self, session_id: str = "default") -> Optional[dict]:
        """Get the current active salary info, falling back to most recent."""
        doc = await self.salary.find_one(
            {"active": True, "session_id": session_id},
            sort=[("created_at", -1)],
        )
        if not doc:
            doc = await self.salary.find_one(
                {"session_id": session_id},
                sort=[("created_at", -1)],
            )
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def get_financial_summary(self, session_id: str = "default") -> dict:
        """
        Compute a full financial snapshot.
        This is what the agent uses as context for its analysis.
        """
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        thirty_days_ago_str = thirty_days_ago.strftime("%Y-%m-%d")

        pipeline_spend = [
            {"$match": {
                "type": "debit",
                "date": {"$gte": thirty_days_ago_str},
                "session_id": session_id,
            }},
            {"$group": {
                "_id": "$category",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"total": -1}},
        ]
        spending_by_category = await self.transactions.aggregate(pipeline_spend).to_list(length=50)

        pipeline_inflow = [
            {"$match": {
                "type": "credit",
                "date": {"$gte": thirty_days_ago_str},
                "session_id": session_id,
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$amount"},
            }},
        ]
        inflow_result = await self.transactions.aggregate(pipeline_inflow).to_list(length=1)
        total_inflow = inflow_result[0]["total"] if inflow_result else 0

        total_outflow = sum(c["total"] for c in spending_by_category)

        bills = await self.get_bills(session_id=session_id)
        total_bills_due = sum(b.get("amount", 0) for b in bills)
        salary = await self.get_salary(session_id=session_id)
        txn_count = await self.transactions.count_documents({"session_id": session_id})

        return {
            "period": "last_30_days",
            "total_inflow": round(total_inflow, 2),
            "total_outflow": round(total_outflow, 2),
            "net": round(total_inflow - total_outflow, 2),
            "spending_by_category": [
                {
                    "category": c["_id"] or "uncategorised",
                    "total": round(c["total"], 2),
                    "transactions": c["count"],
                }
                for c in spending_by_category
            ],
            "upcoming_bills": bills,
            "total_bills_due": round(total_bills_due, 2),
            "salary": salary,
            "total_transactions_stored": txn_count,
            "generated_at": now.isoformat(),
        }

    async def get_spending_trend(
        self, category: str, months: int = 3, session_id: str = "default"
    ) -> list:
        """Get monthly spending trend for a category."""
        cutoff = datetime.utcnow() - timedelta(days=months * 30)
        pipeline = [
            {"$match": {
                "type": "debit",
                "category": category,
                "date": {"$gte": cutoff.strftime("%Y-%m-%d")},
                "session_id": session_id,
            }},
            {"$group": {
                "_id": {"$substr": ["$date", 0, 7]},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        result = await self.transactions.aggregate(pipeline).to_list(length=12)
        return result

    async def save_forecast(self, forecast: dict, session_id: str = "default") -> str:
        """Save a generated forecast for history."""
        forecast["session_id"] = session_id
        forecast["created_at"] = datetime.utcnow()
        result = await self.forecasts.insert_one(forecast)
        return str(result.inserted_id)

    async def save_session_message(self, session_id: str, role: str, content: str):
        """Save a chat message to session history."""
        await self.sessions.insert_one({
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
        })

    async def get_session_history(self, session_id: str, limit: int = 10) -> list:
        """Get recent chat history for a session."""
        cursor = self.sessions.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).limit(limit)
        messages = await cursor.to_list(length=limit)
        messages.reverse()
        for m in messages:
            m["_id"] = str(m["_id"])
        return messages
