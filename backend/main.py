"""
BillGuard — AI Finance Agent for African Professionals
Backend: FastAPI + Gemini Agent + MongoDB
"""

import logging
import os
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

load_dotenv()

from agent import BillGuardAgent
from db import MongoDBClient
from parser import BankStatementParser

db_client: MongoDBClient | None = None
agent: BillGuardAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise MongoDB client and agent at startup."""
    global db_client, agent
    db_client = MongoDBClient()
    try:
        await db_client.create_indexes()
        await db_client.ping()
        logger.info("MongoDB connected")
    except Exception as exc:
        logger.error("MongoDB startup failed: %s", exc)
        raise RuntimeError(
            "Cannot connect to MongoDB. Check MONGODB_URI and Atlas Network Access "
            "(allow 0.0.0.0/0 for Railway/Vercel)."
        ) from exc
    agent = BillGuardAgent(db_client)
    yield


app = FastAPI(title="BillGuard API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"


class BillEntry(BaseModel):
    name: str
    amount: float
    due_date: str
    category: str
    currency: str = "NGN"
    session_id: str = "default"


class SalaryInfo(BaseModel):
    amount: float
    pay_date: str
    currency: str = "NGN"
    session_id: str = "default"


@app.get("/health")
async def health():
    db_ok = False
    if db_client:
        try:
            await db_client.ping()
            db_ok = True
        except Exception:
            pass
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "BillGuard",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/upload-statement")
async def upload_statement(
    file: UploadFile = File(...),
    session_id: str = Form(default="default"),
):
    """Accept a CSV bank statement, parse, and store transactions in MongoDB."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()

    text = None
    for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1"]:
        try:
            text = content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        text = content.decode("utf-8", errors="ignore")

    parser = BankStatementParser()
    transactions = parser.parse(text)

    if not transactions:
        lines = text.splitlines()
        header_preview = lines[0][:150] if lines else "empty"
        raise HTTPException(
            status_code=400,
            detail=(
                f"No transactions found. First line of your file: '{header_preview}'. "
                "Please make sure this is a CSV bank statement export."
            ),
        )

    stored = await db_client.store_transactions(transactions, session_id)

    return {
        "success": True,
        "transactions_imported": stored,
        "message": f"Successfully imported {stored} transactions into BillGuard",
    }


@app.post("/api/bills")
async def add_bill(bill: BillEntry):
    """Add an upcoming bill for the agent to factor in."""
    result = await db_client.store_bill(bill.model_dump(), bill.session_id)
    return {"success": True, "bill_id": result}


@app.get("/api/bills")
async def get_bills(session_id: str = "default", include_paid: bool = False):
    """Get bills. By default only unpaid; set include_paid=true for all."""
    bills = await db_client.get_bills(include_paid=include_paid, session_id=session_id)
    return {"bills": bills}


@app.patch("/api/bills/{bill_id}/paid")
async def mark_bill_paid(bill_id: str, session_id: str = "default"):
    await db_client.mark_bill_paid(bill_id, session_id)
    return {"success": True}


@app.delete("/api/bills/{bill_id}")
async def delete_bill(bill_id: str, session_id: str = "default"):
    await db_client.delete_bill(bill_id, session_id)
    return {"success": True}


@app.post("/api/salary")
async def set_salary(salary: SalaryInfo):
    """Set salary information for forecasting."""
    await db_client.store_salary(salary.model_dump(), salary.session_id)
    return {"success": True, "message": "Salary info saved"}


@app.post("/api/chat")
async def chat(body: ChatMessage):
    """Stream agent reasoning and response via Server-Sent Events."""

    async def stream_response():
        try:
            async for chunk in agent.chat(body.message, body.session_id):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/summary")
async def get_summary(session_id: str = "default"):
    """Get a quick financial summary without the full agent."""
    summary = await db_client.get_financial_summary(session_id=session_id)
    return summary


@app.get("/api/transactions")
async def get_transactions(
    session_id: str = "default",
    limit: int = 50,
    category: Optional[str] = None,
):
    """Get stored transactions, optionally filtered by category."""
    txns = await db_client.get_transactions(
        limit=limit, category=category, session_id=session_id
    )
    return {"transactions": txns, "count": len(txns)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
