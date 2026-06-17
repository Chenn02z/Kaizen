# Deployment

Kaizen needs an always-on HTTPS web service plus persistent PostgreSQL with
pgvector. Static hosting is not enough because Telegram sends updates to the
FastAPI webhook, the scheduler runs with the API process, and the Telegram Mini
App is served from the same public origin.

The default deployment target is Render:

- `render.yaml` defines one paid `starter` web service and one `basic-256mb`
  Postgres database in the Singapore region.
- `scripts/render-build.sh` installs Python dependencies, installs Mini App
  dependencies, and builds `webapp/dist`.
- The Render pre-deploy command runs Alembic migrations and idempotently loads
  the RAG corpus into pgvector.
- Runtime starts FastAPI with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

Render's free instances are not a good fit for daily use: free web services spin
down after idle time, and free Postgres databases expire. Use free only for a
temporary deploy test.

## 1. Create the Render blueprint

1. Push the repository to GitHub or GitLab.
2. In Render, create a new Blueprint from the repo.
3. Keep the `kaizen` web service and `kaizen-db` database from `render.yaml`.
4. Fill the prompted environment variables:
   - `TELEGRAM_TOKEN`
   - `ALLOWED_USER_ID`
   - `LLM_API_KEY`
   - `EMBED_API_KEY`
   - `PUBLIC_URL`
   - `APP_TIMEZONE`, if your quiet hours should not use `Asia/Singapore`
   - optional: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `MEM0_API_KEY`

Set `PUBLIC_URL` to the final HTTPS origin, for example
`https://kaizen.onrender.com` or your custom domain. Do not include a trailing
slash.

Keep the web service at one running instance while the scheduler is in-process;
scaling the API horizontally would make multiple schedulers eligible to fire.

## 2. Confirm the deploy

After Render finishes deploying:

```bash
curl https://<PUBLIC_URL_HOST>/health
```

Expected response:

```json
{"status":"ok"}
```

Also open `https://<PUBLIC_URL_HOST>/miniapp`. It should return the built Mini
App instead of `503`.

## 3. Register Telegram

Register the webhook with the same `TELEGRAM_WEBHOOK_SECRET` stored in Render:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook" \
  -d "url=<PUBLIC_URL>/webhook" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

Telegram sends that value back as `X-Telegram-Bot-Api-Secret-Token`; Kaizen
rejects webhook calls without it.

In BotFather, set the Mini App domain to the public HTTPS host. Then restart or
redeploy the Render web service so startup registers the bot menu button using
`PUBLIC_URL`.

## 4. Smoke test

1. Send `/start` to the bot from the allowed Telegram account.
2. Confirm the reply contains an `Open Dashboard` Mini App button.
3. Send a normal `log`, such as `read for 20 minutes and went to the gym`.
4. Confirm the bot replies and `logs` has a new row in Render Postgres.
5. Open the dashboard from Telegram and confirm the recent log appears.

If `/start` says the dashboard is not configured, set `PUBLIC_URL` in Render and
redeploy.
