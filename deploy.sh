#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

can_sudo() {
  command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1
}

create_venv() {
  if python3 -m venv .venv; then
    return 0
  fi

  echo "[deploy] python3 -m venv failed, trying fallbacks..."

  if can_sudo; then
    sudo apt-get update
    sudo apt-get install -y python3-venv
    python3 -m venv .venv
    return 0
  fi

  python3 -m pip install --user virtualenv
  python3 -m virtualenv .venv
}

ensure_node() {
  if command -v npm >/dev/null 2>&1; then
    return 0
  fi

  if can_sudo; then
    echo "[deploy] npm not found, installing nodejs/npm..."
    sudo apt-get update
    sudo apt-get install -y nodejs npm
    return 0
  fi

  echo "[deploy] npm not found and sudo unavailable. Cannot build frontend."
  exit 1
}

start_backend() {
  if [ -d ".venv" ] && [ ! -f ".venv/bin/activate" ]; then
    echo "[deploy] broken .venv detected, recreating..."
    rm -rf .venv
  fi

  if [ ! -f ".venv/bin/activate" ]; then
    create_venv
  fi

  . .venv/bin/activate

  # 只在 requirements.api.txt 有变化时才重装依赖
  REQ_HASH_FILE=".venv/.req_hash"
  REQ_HASH_NOW="$(md5sum requirements.api.txt | cut -d' ' -f1)"
  REQ_HASH_PREV="$(cat "$REQ_HASH_FILE" 2>/dev/null || echo '')"

  if [ "$REQ_HASH_NOW" != "$REQ_HASH_PREV" ]; then
    echo "[deploy] requirements.api.txt changed, reinstalling dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.api.txt
    echo "$REQ_HASH_NOW" > "$REQ_HASH_FILE"
  else
    echo "[deploy] requirements.api.txt unchanged, skipping pip install"
  fi

  mkdir -p logs

  if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
    pkill -f "uvicorn app.main:app"
    sleep 1
  fi

  nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
  echo "[deploy] API started on port 8000"
}

build_frontend() {
  ensure_node
  cd "$APP_DIR/frontend"

  # 只在 package-lock.json 有变化时才重装 node_modules
  LOCK_HASH_FILE="node_modules/.lock_hash"
  LOCK_HASH_NOW="$(md5sum package-lock.json | cut -d' ' -f1)"
  LOCK_HASH_PREV="$(cat "$LOCK_HASH_FILE" 2>/dev/null || echo '')"

  if [ "$LOCK_HASH_NOW" != "$LOCK_HASH_PREV" ]; then
    echo "[deploy] package-lock.json changed, reinstalling node_modules..."
    npm ci --no-audit --no-fund
    echo "$LOCK_HASH_NOW" > "$LOCK_HASH_FILE"
  else
    echo "[deploy] package-lock.json unchanged, skipping npm install"
  fi

  npm run build
  cd "$APP_DIR"
  echo "[deploy] Frontend build completed"
}

publish_frontend() {
  if ! can_sudo; then
    echo "[deploy] sudo is required to publish frontend files"
    exit 1
  fi

  sudo mkdir -p /var/www/vibecheck
  sudo rsync -a --delete "$APP_DIR/frontend/dist/" /var/www/vibecheck/
  sudo find /var/www/vibecheck -type d -exec chmod 755 {} \;
  sudo find /var/www/vibecheck -type f -exec chmod 644 {} \;

  echo "[deploy] Frontend published to /var/www/vibecheck"
}

configure_nginx() {
  if ! can_sudo; then
    echo "[deploy] sudo is required to configure nginx"
    exit 1
  fi

  if ! command -v nginx >/dev/null 2>&1; then
    echo "[deploy] nginx not found, installing..."
    sudo apt-get update
    sudo apt-get install -y nginx
  fi

  sudo tee /etc/nginx/sites-available/vibecheck >/dev/null <<EOF
server {
    listen 80;
    server_name _;

    root /var/www/vibecheck;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }

    location = /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
    }

    location = /redoc {
        proxy_pass http://127.0.0.1:8000/redoc;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location = /index.html {
        try_files \$uri =404;
    }
}
EOF

  sudo ln -sfn /etc/nginx/sites-available/vibecheck /etc/nginx/sites-enabled/vibecheck
  sudo rm -f /etc/nginx/sites-enabled/default
  sudo nginx -t
  sudo systemctl enable nginx
  sudo systemctl restart nginx
  echo "[deploy] Nginx configured on port 80"
}

# 后端和前端独立部署，互不影响
BACKEND_OK=true
FRONTEND_OK=true

start_backend || { echo "[deploy] WARNING: backend deployment failed, continuing with frontend..."; BACKEND_OK=false; }
build_frontend || { echo "[deploy] WARNING: frontend build failed"; FRONTEND_OK=false; }

if [ "$FRONTEND_OK" = true ]; then
  publish_frontend || { echo "[deploy] WARNING: frontend publish failed"; FRONTEND_OK=false; }
fi

configure_nginx || echo "[deploy] WARNING: nginx configuration failed"

echo ""
echo "[deploy] ========== Deployment Summary =========="
echo "[deploy] Backend:  $([ "$BACKEND_OK" = true ] && echo 'OK' || echo 'FAILED')"
echo "[deploy] Frontend: $([ "$FRONTEND_OK" = true ] && echo 'OK' || echo 'FAILED')"
echo "[deploy] Frontend: http://<server-ip>/"
echo "[deploy] Backend docs: http://<server-ip>/docs"

# 任何一个失败都以非零退出，让 CI 报错
if [ "$BACKEND_OK" = false ] || [ "$FRONTEND_OK" = false ]; then
  exit 1
fi
