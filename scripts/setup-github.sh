#!/usr/bin/env bash
# Initialise billguard as its own git repo and push to GitHub for Vercel/Render
set -euo pipefail

REPO_NAME="${1:-billguard}"
GITHUB_USER="${2:-}"

cd "$(dirname "$0")/.."

if [[ ! -d .git ]]; then
  git init -b main
  git add .
  git commit -m "BillGuard: AI Finance Agent for African Professionals"
  echo "✓ Local git repo created"
else
  echo "Git repo already exists"
fi

if [[ -n "$GITHUB_USER" ]]; then
  echo ""
  echo "Create repo at: https://github.com/new?name=$REPO_NAME"
  echo "Then run:"
  echo "  git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git"
  echo "  git push -u origin main"
else
  echo ""
  echo "Next steps:"
  echo "  1. Create repo: https://github.com/new  (name: $REPO_NAME)"
  echo "  2. git remote add origin https://github.com/YOUR_USER/$REPO_NAME.git"
  echo "  3. git push -u origin main"
fi
