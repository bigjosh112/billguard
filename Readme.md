# BillGuard 🛡️
### AI Finance Agent for African Professionals

> **Built for the Google Cloud Rapid Agent Hackathon 2026 — MongoDB Track**

BillGuard is an AI agent that helps working professionals in Nigeria and Africa take control of their finances. It ingests your bank statement, stores all transactions in MongoDB Atlas, and then uses Gemini to reason over your real data — prioritising bills, forecasting your cash flow, and identifying hidden spending.

---

## The Problem

Every month, millions of African professionals face the same mental load:
- Salary arrives. Bills pile up simultaneously.
- Rent, loan repayments, utilities, subscriptions, food — all due within the same window.
- No clear picture of what to pay first, what can wait, and whether you'll make it to the next payday.

Most finance apps are built for the US. BillGuard is built for Lagos.

---

## What BillGuard Does

| Step | Action |
|------|--------|
| **1. Ingest** | Upload your bank CSV (GTBank, Access, Zenith, UBA, First Bank) |
| **2. Store** | Agent normalises and stores every transaction in MongoDB Atlas via MCP |
| **3. Categorise** | Gemini automatically categorises spending — rent, transport, food, subscriptions, loans |
| **4. Prioritise** | Given your current balance, the agent tells you exactly which bills to pay first |
| **5. Forecast** | Projects your cash flow to your next salary date — will you make it? |
| **6. Recommend** | Identifies forgotten subscriptions and specific things you can cut |

---

## Tech Stack

- **AI Agent**: Gemini 2.0 Flash via Google Cloud Agent Builder
- **Database**: MongoDB Atlas (via MCP — central to the agent's memory)
- **Backend**: Python + FastAPI deployed on Google Cloud Run
- **Frontend**: Next.js with real-time streaming agent responses
- **MCP Integration**: MongoDB MCP server — every agent tool call reads/writes MongoDB

---

## Architecture

```
User → Next.js Chat UI
         ↓
    FastAPI Backend
         ↓
  BillGuard Gemini Agent
    ↓         ↓         ↓
get_summary  prioritise  get_transactions
    ↓         ↓         ↓
         MongoDB Atlas (MCP)
         [transactions, bills, salary, forecasts, sessions]
```

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account (free M0 tier works)
- Google AI Studio API key (free)

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB URI and Gemini API key

# Verify connections (optional)
python test_connection.py

# Seed demo data (optional but recommended for testing)
python seed_demo.py

# Start the backend
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

# Start
npm run dev
```

Then open http://localhost:3000

---

## Hosting for the Hackathon

Deploy to production in ~20 minutes:

- **Backend** → Google Cloud Run (Dockerfile included)
- **Frontend** → Vercel
- **Database** → MongoDB Atlas (already set up)

Full step-by-step guide: **[DEPLOY.md](./DEPLOY.md)**

Quick deploy:

```bash
export GCP_PROJECT_ID=your-project
export MONGODB_URI="mongodb+srv://..."
export GEMINI_API_KEY="your-key"
./scripts/deploy-backend.sh

export NEXT_PUBLIC_API_URL=https://your-cloud-run-url.run.app
./scripts/deploy-frontend.sh
```

**Important:** In MongoDB Atlas → Network Access, allow `0.0.0.0/0` so Cloud Run can connect.

---

## Demo Flow

1. Upload a bank statement CSV (or use the pre-seeded demo data)
2. Add upcoming bills with due dates
3. Enter your salary amount and next pay date
4. Ask BillGuard: **"I have ₦87,000 in my account. What do I pay first?"**
5. Watch the agent reason step by step, query MongoDB, and produce a prioritised plan

---

## MongoDB MCP Integration

MongoDB Atlas is not just a storage layer — it's the agent's working memory.

The agent has 5 MCP-backed tools:
- `get_financial_summary` — aggregation pipeline over transactions collection
- `get_transactions` — filtered query with category index
- `get_bills` — sorted bill schedule
- `get_salary_info` — active salary document
- `prioritise_bills` — reads from all collections to run forecast algorithm

Remove MongoDB and the agent has no memory, no data, no context. It's central.

---

## License

MIT License — see LICENSE file.

---

*Built in Lagos, Nigeria. For everyone counting days to payday.*