#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/CustomerPulse}"
BRANCH="${BRANCH:-dev}"

if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "PROJECT_DIR must point to a cloned CustomerPulse repository: $PROJECT_DIR" >&2
  exit 1
fi

cd "$PROJECT_DIR"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [ ! -f ".env" ]; then
  echo ".env is missing. Create it from .env.template and fill real secrets before deploying." >&2
  exit 1
fi

docker compose build
docker compose up -d
docker compose ps
