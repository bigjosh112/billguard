# Deploy BillGuard for Devpost

**Recommended stack:** Railway backend + Vercel frontend + MongoDB Atlas + Gemini

| Layer | Service | Cost |
|-------|---------|------|
| Backend | **Railway** | Free tier / trial credits |
| Frontend | **Vercel** | Free |
| Database | **MongoDB Atlas M0** | Free |
| AI | **Gemini API** | Free |

**Live URLs:**
- Frontend: https://billguard-six.vercel.app
- GitHub: https://github.com/bigjosh112/billguard

---

## Path A: Railway backend (recommended)

### 1. MongoDB Atlas

Network Access → **Allow `0.0.0.0/0`**

### 2. Deploy API on Railway

1. [railway.com](https://railway.com) → **New Project** → **Deploy from GitHub repo**
2. Select **`bigjosh112/billguard`**
3. **Service Settings:**
   - **Root Directory:** `backend`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Healthcheck Path:** `/health`
4. Railway reads [`backend/railway.toml`](backend/railway.toml) automatically
5. **Variables** — on the **service** (not project), click **Variables** tab, paste from `backend/.env`:
   - `MONGODB_URI`
   - `GEMINI_API_KEY`
   - `ENVIRONMENT=production`

   > If healthcheck fails, you likely forgot these. The app needs `MONGODB_URI` to connect to Atlas.
6. **Settings → Networking → Generate Domain** → copy URL  
   (e.g. `https://billguard-api-production.up.railway.app`)

Verify:

```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/health
# Must show: "service": "BillGuard", "database": "connected"
```

### 3. Connect Vercel to Railway

1. [Vercel](https://vercel.com) → **billguard** → **Settings → Environment Variables**
2. Set **`BILLGUARD_API_URL`** = your Railway URL (no trailing slash)
3. **Deployments → Redeploy** production

The frontend proxies via `/backend/api/...` — no CORS setup needed.

### 4. Keep-alive for judges

Set GitHub repo variable so the keep-alive workflow works:

**GitHub repo → Settings → Secrets and variables → Actions → Variables → New:**
- Name: `BILLGUARD_API_URL`
- Value: `https://YOUR-RAILWAY-URL.up.railway.app`

Workflow: [`.github/workflows/keep-warm.yml`](.github/workflows/keep-warm.yml) pings every 10 minutes.

### 5. Seed demo data

```bash
cd backend && python seed_demo.py
```

Judges can load demo data:

```javascript
localStorage.setItem('billguard_session_id', 'demo_session');
location.reload();
```

### 6. Decommission Render (after Railway works)

1. Verify Railway health + Vercel upload/chat work
2. Render dashboard → **billguard-api** → **Delete**
3. Remove old Render URL from any bookmarks

---

## Path B: Google Cloud Run (GCP hackathon track)

Requires billing: https://console.cloud.google.com/billing

```bash
export GCP_PROJECT_ID=your-project
export MONGODB_URI="mongodb+srv://..."
export GEMINI_API_KEY="..."
./scripts/deploy-backend.sh
```

Set `BILLGUARD_API_URL` on Vercel to your Cloud Run URL.

---

## Path C: Render (legacy)

See [`render.yaml`](render.yaml). Not recommended — use Railway instead.

---

## Vercel frontend (already deployed)

- **Root Directory:** `frontend`
- **Env var:** `BILLGUARD_API_URL` = Railway backend URL
- **Live:** https://billguard-six.vercel.app

CLI redeploy:

```bash
cd frontend
printf 'https://YOUR-RAILWAY-URL.up.railway.app' | npx vercel env add BILLGUARD_API_URL production
npx vercel --prod --yes
```

---

## Verification checklist

- [ ] `curl RAILWAY_URL/health` → `"service":"BillGuard","database":"connected"`
- [ ] `curl billguard-six.vercel.app/backend/health` → same via proxy
- [ ] CSV upload works on live site
- [ ] Chat streams agent responses
- [ ] Demo session works (`demo_session`)
- [ ] GitHub Action "Keep Backend Warm" runs successfully

---

## Troubleshooting

### `BILLGUARD_API_URL not set on Vercel`

Add Railway URL in Vercel env vars and redeploy.

### Backend timeout / "Server is waking up"

- Wait for "Connecting to server…" banner to finish
- Upload/chat auto-retry up to 4 times
- Open site 1–2 min before demo, or use demo mode

### `MongoDB startup failed`

Atlas → Network Access → allow `0.0.0.0/0`. Check `MONGODB_URI` on Railway.

### Gemini 429 quota

Agent falls back to rule-based responses. Add fresh API key for full AI.

---

## Architecture

```
User → Vercel (billguard-six.vercel.app)
         ↓  /backend/* proxy
    Railway (FastAPI + Agent)
         ↓
    MongoDB Atlas + Gemini API
```

---

## Devpost demo tip

Lead with **demo mode** — no upload, no cold start:

```javascript
localStorage.setItem('billguard_session_id', 'demo_session');
location.reload();
```

Then ask: *"I have ₦20,000. Help me sort my bills from my ₦530,000 salary"*
