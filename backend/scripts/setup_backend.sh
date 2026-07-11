#!/usr/bin/env bash
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BACKEND_DIR"

python3 -m venv .venv
. .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

export PYTHONPATH=.

SETUP_ARGS=(--yes)
if [[ "${SKIP_BEDROCK:-false}" == "true" ]]; then
  SETUP_ARGS+=(--skip-bedrock)
fi
if [[ "${VERIFY_EMBEDDING:-true}" == "true" ]]; then
  SETUP_ARGS+=(--verify-embedding)
fi

python -m app.db.setup "${SETUP_ARGS[@]}"
