---
name: kaizen-frontend
description: "Build and edit the Kaizen Telegram Mini App in webapp plus the FastAPI serving glue for /miniapp and related JSON endpoints."
---

# Kaizen Frontend

Use this skill for Telegram Mini App UI, dashboard, and frontend-serving glue.

## Scope

- `webapp/`
- FastAPI glue serving the built app at `/miniapp`
- JSON endpoints consumed by the Mini App, especially `/me`

## Workflow

1. Read `AGENTS.md` and `docs/PRODUCT.md`.
2. Inspect existing `webapp/` components, API calls, theme usage, and build
   setup before editing.
3. Treat the frontend as a pure client of the existing JSON API.
4. If UI needs new data, extend the backend source of truth rather than faking
   fields in the client.
5. Run `npm run build` in `webapp/` for frontend changes when dependencies are
   available.

## Rules

- Use Telegram theme variables and SDK/theme integration. Do not hardcode a
  palette that ignores Telegram light/dark theme.
- Respect the single-user model and existing guards around `/me`.
- Never hardcode secrets; inject server-side values through config.
- Keep dependencies lean and tree-shakable.
- Do not add analytics or third-party calls beyond the app backend.
- Commit source, not `node_modules/` or built bundles.
