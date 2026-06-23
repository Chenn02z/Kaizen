#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

uv sync --locked
npm ci --prefix webapp
npm run build --prefix webapp
