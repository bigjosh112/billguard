# Deploy BillGuard for Devpost

**Fastest path (no GCP billing):** Render backend + Vercel frontend — ~15 min  
**Hackathon path (GCP track):** Cloud Run + Vercel — requires [billing on GCP](https://console.cloud.google.com/billing) (free tier, ~$0 for demo traffic)

| Layer | Service | Cost |
|-------|---------|------|
| Backend | **Render** or **Cloud Run** | Free |
| Frontend | **Vercel** | Free |
| Database | **MongoDB Atlas M0** | Free |
| AI | **Gemini API** | Free |

---

## Step 0: GitHub ✅ DONE

**Repo:** https://github.com/bigjosh112/billguard

---

## Path A: Render backend (no GCP billing) ⭐ fastest

### 1. MongoDB Atlas
Network Access → **Allow `0.0.0.0/0`**

### 2. Deploy API on Render

**One-click:** https://dashboard.render.com/blueprint/new?repo=https://github.com/bigjosh112/billguard

1. Sign in with GitHub → approve access to `billguard` repo  
2. Render reads `render.yaml` → click **Apply**  
3. When prompted, paste from your `backend/.env`:
   - `MONGODB_URI`
   - `GEMINI_API_KEY`
4. Wait ~5 min → copy URL from **Render dashboard → billguard-api → Settings → URL**  
   (e.g. `https://billguard-api-gjxg.onrender.com` — **not** always `billguard-api.onrender.com`)

Verify:

```bash
curl https://YOUR-ACTUAL-RENDER-URL.onrender.com/health
# Must show: "service": "BillGuard", "database": "connected"
```

> Free tier sleeps after 15 min idle — first load takes ~30s. Fine for Devpost judges.

### 3. Deploy frontend on Vercel

1. **Vercel** → your `billguard` project → **Settings** → **Environment Variables**  
2. Add (Production):
   - `BILLGUARD_API_URL` = your **actual** Render URL (from Render Settings → URL)
3. **Deployments** → ⋯ on latest → **Redeploy** (required — env vars are baked in at build time)

The frontend calls `/backend/api/...` on Vercel, which proxies to Render (no CORS issues).

**Verify backend is FastAPI** (not Express):
```bash
curl https://billguard-api.onrender.com/health
# Must show: "service": "BillGuard", "database": "connected"
```
If you see only `{"status":"ok"}` or `Cannot POST /api/...`, your Render service is wrong — see **Render fix** below.

### 4. Seed demo data

```bash
cd backend && python seed_demo.py
```

---

## Path B: Google Cloud Run (hackathon GCP track)

**Requires billing:** https://console.cloud.google.com/billing → Link project `gen-lang-client-0399705836`

---

## 1. MongoDB Atlas (if not done)

1. Create a free M0 cluster at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. **Database Access** → create user with read/write
3. **Network Access** → **Add IP Address** → **Allow Access from Anywhere** (`0.0.0.0/0`)  
   Required for Cloud Run (IPs change per request)
4. **Connect** → Drivers → copy connection string into `MONGODB_URI`

---

## 2. Google Cloud — Backend on Cloud Run

### Install gcloud

```bash
# macOS
brew install google-cloud-sdk

# Or: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud auth application-default login
```

### Create project

```bash
export GCP_PROJECT_ID=your-hackathon-project-id
gcloud projects create $GCP_PROJECT_ID   # skip if project exists
gcloud config set project $GCP_PROJECT_ID
```

Enable billing on the project (Cloud Run free tier still needs a billing account linked).

### Deploy

```bash
export MONGODB_URI="mongodb+srv://user:pass@cluster....mongodb.net/billguard?retryWrites=true&w=majority"
export GEMINI_API_KEY="your_gemini_key"

chmod +x scripts/deploy-backend.sh
./scripts/deploy-backend.sh
```

Or manually:

```bash
cd backend
gcloud run deploy billguard-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --timeout 300 \
  --set-env-vars "MONGODB_URI=$MONGODB_URI,GEMINI_API_KEY=$GEMINI_API_KEY"
```

Copy the URL printed, e.g. `https://billguard-api-xxxxx-uc.a.run.app`

Verify:

```bash
curl https://YOUR-BACKEND-URL/health
# {"status":"ok","database":"connected",...}
```

### Seed demo data (optional, for judges)

Run locally pointing at production Atlas:

```bash
cd backend
# .env already has MONGODB_URI
python seed_demo.py
```

Judges can load demo data in the browser:

```javascript
localStorage.setItem('billguard_session_id', 'demo_session');
location.reload();
```

---

## 3. Vercel — Frontend

### Option A: Vercel dashboard (easiest)

1. Push repo to GitHub
2. [vercel.com/new](https://vercel.com/new) → Import `billguard` repo
3. **Root Directory**: `frontend`
4. **Environment Variable**:
   - `NEXT_PUBLIC_API_URL` = your Cloud Run URL (no trailing slash)
5. Deploy

### Option B: CLI

```bash
export NEXT_PUBLIC_API_URL=https://billguard-api-xxxxx-uc.a.run.app
chmod +x scripts/deploy-frontend.sh
./scripts/deploy-frontend.sh
```

---

## 4. Submission checklist

- [ ] Live app URL (Vercel frontend)
- [ ] `/health` returns `database: connected`
- [ ] Upload CSV works
- [ ] Chat streams agent responses
- [ ] Demo session works (`demo_session`)
- [ ] GitHub repo is public
- [ ] README mentions MongoDB + Gemini + Cloud Run

---

## Troubleshooting

### Render backend returns `Cannot POST /api/...` (Express error)

Your Render service is **not running the FastAPI Docker image**. Fix:

1. Render dashboard → **billguard-api** → **Settings**
2. Confirm **Runtime: Docker** and Dockerfile path = `backend/Dockerfile`, root = `backend`
3. If it says Node/Python native → **delete service** and redeploy via Blueprint:  
   https://dashboard.render.com/blueprint/new?repo=https://github.com/bigjosh112/billguard
4. After deploy, `curl .../health` must return `"service": "BillGuard"`

### `Failed to fetch` on Vercel

1. Set `NEXT_PUBLIC_API_URL` on Vercel to your Render URL
2. Set `NEXT_PUBLIC_API_PROXY=1`
3. **Redeploy** Vercel (env vars only apply after rebuild)
4. Render free tier sleeps — first request after idle takes ~30s

### `MongoDB startup failed` / DNS timeout locally

Your network DNS (`192.168.x.x`) may block Atlas SRV lookups. Fixes:

- Switch to mobile hotspot or different Wi‑Fi
- Use Google DNS: System Settings → Network → DNS → `8.8.8.8`, `8.8.4.4`
- Cloud Run does not have this issue once Atlas allows `0.0.0.0/0`

### CORS errors

Backend already allows all origins (`allow_origins=["*"]`). If issues persist, confirm `NEXT_PUBLIC_API_URL` has no trailing slash and uses `https://`.

### Gemini 429 quota

Agent falls back to rule-based responses when Gemini is rate-limited. For demo, that still works. Add a fresh API key for full AI.

### Cloud Run cold start

First request after idle may take 3–5s. Set `--min-instances 1` if demo timing is critical (small cost).

---

## Architecture (production)

```
User → Vercel (Next.js)
         ↓  NEXT_PUBLIC_API_URL
    Cloud Run (FastAPI + Agent)
         ↓
    MongoDB Atlas
    Gemini API
```

---

## Keep backend awake for judges (important)

Render **free tier sleeps after 15 minutes**. Three layers prevent cold-start timeouts:

### 1. Automatic keep-alive (already set up)
GitHub Action pings your API **every 10 minutes**:
`.github/workflows/keep-warm.yml`

Check it runs: GitHub repo → **Actions** → "Keep Render Warm" → enable if paused.

### 2. Wake on page load
When a judge opens the site, a **"Starting server…"** banner appears while the backend wakes (up to ~60s). No action needed.

### 3. Before your live demo
Open **https://billguard-six.vercel.app** 1–2 minutes before presenting.  
Or run:
```bash
curl https://billguard-api-gjxg.onrender.com/health
```

### Optional: Render paid ($7/mo)
Render → billguard-api → **Upgrade to Starter** = always on, zero cold starts.

### Devpost demo tip
Tell judges to use **demo mode** (no upload needed):
```javascript
localStorage.setItem('billguard_session_id', 'demo_session');
location.reload();
```

---
