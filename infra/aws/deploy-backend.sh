#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/CustomerPulse}"
BRANCH="${BRANCH:-final-temp}"
COMPOSE_COMMAND="${COMPOSE_COMMAND:-docker compose}"
read -r -a COMPOSE <<< "$COMPOSE_COMMAND"

if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "PROJECT_DIR must point to a cloned CustomerPulse repository: $PROJECT_DIR" >&2
  exit 1
fi

cd "$PROJECT_DIR"
git fetch --prune origin "$BRANCH"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git switch "$BRANCH"
else
  git switch --track -c "$BRANCH" "origin/$BRANCH"
fi
git pull --ff-only origin "$BRANCH"

if [ ! -f ".env" ]; then
  echo ".env is missing. Create it from .env.template and fill real secrets before deploying." >&2
  exit 1
fi

"${COMPOSE[@]}" build backend
"${COMPOSE[@]}" run --rm backend python -m app.db.setup --yes --verify-embedding
"${COMPOSE[@]}" up -d backend
"${COMPOSE[@]}" ps backend
