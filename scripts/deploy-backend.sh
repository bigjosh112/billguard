#!/usr/bin/env bash
# Deploy BillGuard backend to Google Cloud Run
# Prerequisites: gcloud CLI, Docker (or use --source for Cloud Build)
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-billguard-api}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Set GCP_PROJECT_ID to your Google Cloud project ID."
  echo "  export GCP_PROJECT_ID=your-project-id"
  exit 1
fi

if [[ -z "${MONGODB_URI:-}" || -z "${GEMINI_API_KEY:-}" ]]; then
  echo "Set MONGODB_URI and GEMINI_API_KEY in your shell before deploying."
  exit 1
fi

echo "→ Project: $PROJECT_ID | Region: $REGION | Service: $SERVICE_NAME"

gcloud config set project "$PROJECT_ID"

# Enable required APIs (idempotent)
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

cd "$(dirname "$0")/../backend"

ENV_FILE=$(mktemp)
trap 'rm -f "$ENV_FILE"' EXIT
cat > "$ENV_FILE" <<EOF
MONGODB_URI: "${MONGODB_URI}"
GEMINI_API_KEY: "${GEMINI_API_KEY}"
ENVIRONMENT: production
EOF

echo "→ Building and deploying to Cloud Run (3–5 min)..."
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --timeout 300 \
  --env-vars-file "$ENV_FILE" \
  --min-instances 0 \
  --max-instances 3

URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')
echo ""
echo "✓ Backend live at: $URL"
echo "  Health check: $URL/health"
echo ""
echo "Next: deploy frontend with NEXT_PUBLIC_API_URL=$URL"
