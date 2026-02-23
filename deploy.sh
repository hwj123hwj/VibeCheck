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
  echo "[deploy] API started on port 8000"
}

build_frontend() {
  ensure_node
  cd "$APP_DIR/frontend"
  npm ci --no-audit --no-fund
  npm run build
  cd "$APP_DIR"
  echo "[deploy] Frontend build completed"
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

    root $APP_DIR/frontend/dist;
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
        try_files \$uri /index.html;
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

start_backend
build_frontend
configure_nginx

echo "[deploy] Full deployment completed"
echo "[deploy] Frontend: http://<server-ip>/"
echo "[deploy] Backend docs: http://<server-ip>/docs"
