#!/usr/bin/env bash
# INUNDA — one-command demo launcher
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== INUNDA backend ==="
cd "$ROOT/backend"
python -m pip install -q -r requirements.txt
PYTHONPATH=. python -m pytest -q || true
PYTHONPATH=. nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/inunda_api.log 2>&1 &
echo "API on http://localhost:8000"

echo "=== INUNDA frontend ==="
cd "$ROOT/frontend"
npm install --silent
npm run build
nohup npm run dev > /tmp/inunda_ui.log 2>&1 &
echo "UI on http://localhost:5173"
echo "API docs: http://localhost:8000/docs"
echo "Logs: /tmp/inunda_api.log  /tmp/inunda_ui.log"
