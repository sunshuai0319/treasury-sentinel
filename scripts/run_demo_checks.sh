#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR/apps/api"
uv run pytest -q
PYTHONPATH=../..:. uv run python ../../knowledge/scripts/ingest_policies.py --dry-run
PYTHONPATH=../..:. uv run python ../../knowledge/scripts/evaluate_retrieval.py --offline --golden ../../knowledge/fixtures/rag-golden-set.json

cd "$ROOT_DIR/contracts"
npm test

cd "$ROOT_DIR/apps/web"
npm run build

