# Devpost Submission — BillGuard

Copy these into your [Devpost](https://devpost.com) project page.

---

## Project name
**BillGuard: AI Finance Agent for African Professionals**

## Tagline (one line)
Your AI finance friend that reads your bank statement, remembers your bills, and tells you what to pay first — honestly.

## Inspiration
Every month, millions of Nigerian professionals face the same stress: salary lands, rent, loans, utilities, and subscriptions all hit at once — with no clear plan for what to pay first. US finance apps don't understand Lagos reality (EKEDC, Renmoney, PiggyVest, salary on the 25th). We built BillGuard for that.

## What it does
1. **Upload** your bank CSV (GTBank, Access, Zenith, UBA, First Bank)
2. **Store** every transaction in MongoDB Atlas — the agent's working memory
3. **Chat** with an AI agent that prioritises bills, forecasts cash flow, and gives honest advice when salary can't cover everything
4. **Negotiate** — drafts messages to landlords and lenders when you're short

## How we built it
- **Gemini 2.0 Flash** — agent reasoning and natural language
- **MongoDB Atlas** — transactions, bills, salary, sessions (agent memory via tools)
- **FastAPI** on **Railway** — streaming SSE chat API
- **Next.js 15** on **Vercel** — real-time agent UI with reasoning steps

## Challenges we ran into
- Nigerian bank CSVs have metadata rows before headers — built a smart header detector
- Agent gave false comfort ("salary covers the rest") when maths didn't add up — rewrote prioritisation with honest shortfall logic
- Session isolation so each user's data stays separate in MongoDB

## Accomplishments
- Full end-to-end agent: upload → categorise → prioritise → forecast → negotiate
- Honest financial maths when bills exceed salary (critical for trust)
- Demo mode with pre-seeded Lagos professional data

## What we learned
MongoDB isn't just storage — it's the agent's memory. Remove it and the agent has no context. Tool-calling + structured prioritisation beats pure LLM advice for money.

## What's next
- Bank API integrations (Mono, Okra)
- WhatsApp bot for bill reminders
- Multi-currency (Ghana, Kenya)

---

## Links to fill in after deploy

| Field | Value |
|-------|--------|
| **Live demo** | https://billguard-six.vercel.app |
| **GitHub** | https://github.com/bigjosh112/billguard |
| **Backend** | Railway (URL in Vercel `BILLGUARD_API_URL`) |
| **Video demo** | (record 2–3 min Loom/YouTube) |

## Demo script for video (2 min)

1. Open live URL → show clean UI
2. Console: `localStorage.setItem('billguard_session_id','demo_session'); location.reload()`
3. Show transactions loaded from MongoDB
4. Ask: *"I have ₦20,000. Help me sort my bills from my ₦530,000 salary"*
5. Show agent reasoning steps + honest shortfall plan
6. Ask: *"Draft a message to my landlord"* → show negotiation draft

## Technologies (for Devpost tags)
`Python` `FastAPI` `Next.js` `MongoDB` `Google Gemini` `Railway` `Vercel` `AI Agents`
