#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

create_venv() {
  if python3 -m venv .venv; then
    return 0
  fi

  echo "[deploy] python3 -m venv failed, trying fallbacks..."

  # Fallback 1: install system package when sudo is available without prompt
  if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3-venv
    python3 -m venv .venv
    return 0
  fi

  # Fallback 2: use virtualenv from user site-packages
  python3 -m pip install --user virtualenv
  python3 -m virtualenv .venv
}

if [ ! -d ".venv" ]; then
  create_venv
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