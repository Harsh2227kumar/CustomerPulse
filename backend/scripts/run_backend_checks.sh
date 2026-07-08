#!/usr/bin/env bash
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "$BACKEND_DIR/.." && pwd)"

cd "$BACKEND_DIR"
export PYTHONPATH=.

python -m unittest discover -s tests -p "test_*.py" -v

if [[ "${SKIP_EMBEDDING:-false}" != "true" ]]; then
  python scripts/download_embedding_model.py --model all-MiniLM-L6-v2 --local-files-only
fi

python -m app.db.setup --help

if [[ "${SKIP_COMPOSE:-false}" != "true" ]]; then
  cd "$REPO_DIR"
  docker compose config --quiet
fi
