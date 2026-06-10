#!/usr/bin/env bash
# Deploy BillGuard frontend to Vercel
set -euo pipefail

API_URL="${NEXT_PUBLIC_API_URL:-}"

if [[ -z "$API_URL" ]]; then
  echo "Set NEXT_PUBLIC_API_URL to your Cloud Run backend URL."
  echo "  export NEXT_PUBLIC_API_URL=https://billguard-api-xxxxx.run.app"
  exit 1
fi

cd "$(dirname "$0")/../frontend"

if ! command -v vercel &>/dev/null; then
  echo "Installing Vercel CLI..."
  npm install -g vercel
fi

echo "→ Deploying frontend (API: $API_URL)"
vercel --prod \
  --env "NEXT_PUBLIC_API_URL=$API_URL" \
  --yes

echo ""
echo "✓ Frontend deployed. Set NEXT_PUBLIC_API_URL in Vercel dashboard if not picked up."
