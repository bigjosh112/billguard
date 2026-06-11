#!/usr/bin/env bash
# Point Vercel + GitHub keep-alive at your Railway backend URL.
# Usage: ./scripts/switch-to-railway.sh https://your-service.up.railway.app
set -euo pipefail

RAILWAY_URL="${1:-}"
if [[ -z "$RAILWAY_URL" ]]; then
  echo "Usage: $0 https://your-service.up.railway.app"
  exit 1
fi
RAILWAY_URL="${RAILWAY_URL%/}"

echo "→ Verifying Railway health..."
curl -sf --max-time 120 "${RAILWAY_URL}/health" | grep -q BillGuard || {
  echo "✗ Railway health check failed. Deploy Railway first (see DEPLOY.md)."
  exit 1
}
echo "✓ Railway OK"

echo "→ Updating Vercel BILLGUARD_API_URL..."
cd "$(dirname "$0")/../frontend"
npx vercel env rm BILLGUARD_API_URL production --yes 2>/dev/null || true
printf '%s' "$RAILWAY_URL" | npx vercel env add BILLGUARD_API_URL production
npx vercel --prod --yes

echo "→ Setting GitHub Actions variable BILLGUARD_API_URL..."
gh variable set BILLGUARD_API_URL --body "$RAILWAY_URL" --repo bigjosh112/billguard 2>/dev/null || \
  echo "  (Set manually: GitHub → Settings → Actions → Variables → BILLGUARD_API_URL)"

echo ""
echo "✓ Done. Frontend now proxies to: $RAILWAY_URL"
echo "  Test: curl https://billguard-six.vercel.app/backend/health"
echo ""
echo "Next: Delete Render service in dashboard (see DEPLOY.md)"
