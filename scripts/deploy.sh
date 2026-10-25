#!/usr/bin/env bash
# Pull, migrate, re-embed changed corpus files, restart. Run on the VM for every release.
set -euo pipefail

APP_DIR=/opt/kaizen/app
ENV_FILE=/opt/kaizen/.env
export PATH="$HOME/.local/bin:$PATH"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE (copy .env.example and fill it in)" >&2; exit 1; }

cd "$APP_DIR"
# pydantic-settings reads .env from the working directory; keep the real file outside the repo.
ln -sf "$ENV_FILE" .env
git pull --ff-only
uv sync --locked --no-dev
uv run --no-sync alembic upgrade head
uv run --no-sync python -m app.rag.load
sudo systemctl restart kaizen
sleep 3
curl -fsS http://127.0.0.1:8000/health && echo " kaizen is up"
