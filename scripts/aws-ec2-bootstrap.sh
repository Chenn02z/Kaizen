#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kaizen/habitbot}"
APP_USER="${APP_USER:-ubuntu}"
ENV_FILE="${ENV_FILE:-/opt/kaizen/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Create it from .env.example with production values first." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y curl git nginx python3 ca-certificates

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

if ! command -v npm >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

sudo mkdir -p /opt/kaizen
sudo chown -R "$APP_USER":"$APP_USER" /opt/kaizen

cd "$APP_DIR"
bash scripts/deploy-build.sh
uv run alembic upgrade head
uv run python -m app.rag.load

sudo install -m 0644 deploy/aws/kaizen.service /etc/systemd/system/kaizen.service
sudo systemctl daemon-reload
sudo systemctl enable kaizen
sudo systemctl restart kaizen

echo "Kaizen service started. Configure Nginx with deploy/aws/nginx.conf.example, then register the Telegram webhook."
