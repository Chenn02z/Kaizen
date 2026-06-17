#!/usr/bin/env bash
set -euo pipefail

uv sync --locked
npm ci --prefix webapp
npm run build --prefix webapp
