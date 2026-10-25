#!/usr/bin/env bash
# One-time setup for an Oracle Cloud Ubuntu VM. Safe to re-run.
# Usage: KAIZEN_HOST=kaizen.example.com bash scripts/oracle-bootstrap.sh
set -euo pipefail

: "${KAIZEN_HOST:?Set KAIZEN_HOST to the public hostname, e.g. 1-2-3-4.sslip.io}"
APP_DIR=/opt/kaizen/app

sudo apt-get update
sudo apt-get install -y curl git debian-keyring debian-archive-keyring apt-transport-https

if ! command -v caddy >/dev/null 2>&1; then
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list
  sudo apt-get update
  sudo apt-get install -y caddy
fi

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Oracle's Ubuntu images ship iptables rules that drop everything except SSH.
for port in 80 443; do
  if ! sudo iptables -C INPUT -m state --state NEW -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$port" -j ACCEPT
  fi
done
sudo netfilter-persistent save

echo "KAIZEN_HOST=$KAIZEN_HOST" | sudo tee /etc/default/caddy >/dev/null
sudo mkdir -p /etc/systemd/system/caddy.service.d
printf '[Service]\nEnvironmentFile=/etc/default/caddy\n' \
  | sudo tee /etc/systemd/system/caddy.service.d/env.conf >/dev/null
sudo install -m 0644 "$APP_DIR/deploy/oracle/Caddyfile" /etc/caddy/Caddyfile
sudo install -m 0644 "$APP_DIR/deploy/oracle/kaizen.service" /etc/systemd/system/kaizen.service
sudo systemctl daemon-reload
sudo systemctl enable caddy kaizen
sudo systemctl restart caddy

bash "$APP_DIR/scripts/deploy.sh"
