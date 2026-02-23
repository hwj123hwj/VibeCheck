#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.api.txt

mkdir -p logs

if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
  pkill -f "uvicorn app.main:app"
  sleep 1
fi

nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
echo "API started on port 8000"
