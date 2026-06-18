# Deployment

Kaizen needs an always-on HTTPS web service plus persistent PostgreSQL with
pgvector. Static hosting is not enough because Telegram sends updates to the
FastAPI webhook, the scheduler runs with the API process, and the Telegram Mini
App is served from the same public origin.

The learning-oriented deployment target is AWS:

- EC2 runs FastAPI, the in-process scheduler, and the built Telegram Mini App.
- RDS PostgreSQL stores logs, facts, habit state, interventions, and pgvector
  corpus embeddings.
- Nginx terminates public HTTP/HTTPS and proxies to Uvicorn on localhost.
- `scripts/deploy-build.sh` installs Python dependencies and builds `webapp/dist`.
- `scripts/aws-ec2-bootstrap.sh` installs runtime packages, runs migrations,
  loads the RAG corpus, and installs the systemd service.

This is the smallest AWS shape that teaches useful primitives without forcing a
serverless rewrite.

## Cost Guardrails

AWS is feasible for learning, but "Free Tier" is not the same as "free forever."
Before creating resources:

1. Create a billing budget and alert.
2. Use one EC2 instance and one RDS PostgreSQL instance.
3. Avoid NAT Gateway, Application Load Balancer, ECS, and multi-AZ RDS for v1.
4. Allow EC2 inbound `22` only from your IP, and `80`/`443` from the internet.
5. Allow RDS inbound `5432` only from the EC2 security group.
6. Stop or delete unused resources when experimenting.

Expect possible charges for public IPv4 addresses and usage beyond free credits
or free-tier limits.

## 1. Create AWS Resources

Use one region consistently. `ap-southeast-1` keeps the server close to the
current `APP_TIMEZONE=Asia/Singapore`; `us-east-1` is often cheaper and has broad
free-tier availability.

Create:

- EC2 Ubuntu LTS instance, `t3.micro` or `t4g.micro` if eligible.
- RDS PostgreSQL, `db.t3.micro` or `db.t4g.micro` if eligible.
- Database name: `kaizen`.
- RDS master user: a secret value, not committed to the repo.
- EC2 security group: inbound `22`, `80`, `443`.
- RDS security group: inbound `5432` from the EC2 security group only.

Do not make RDS publicly accessible unless you intentionally want to practice
public database hardening. The app only needs EC2-to-RDS traffic.

## 2. Prepare DNS

Telegram webhooks and Mini Apps need HTTPS. Point a domain such as
`kaizen.example.com` at the EC2 public IP.

Set `PUBLIC_URL` to the final HTTPS origin, for example
`https://kaizen.example.com`. Do not include a trailing slash.

## 3. Configure Environment

Create `/opt/kaizen/.env` on the EC2 instance from `.env.example`.

Required production values:

```bash
TELEGRAM_TOKEN=
ALLOWED_USER_ID=
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<rds-endpoint>:5432/kaizen
TELEGRAM_WEBHOOK_SECRET=
LLM_API_KEY=
LLM_MODEL=claude-haiku-4-5-20251001
EMBED_API_KEY=
EMBED_MODEL=text-embedding-3-small
PUBLIC_URL=https://kaizen.example.com
MINIAPP_SECRET=
SCHEDULER_SECRET=
APP_TIMEZONE=Asia/Singapore
```

Optional:

```bash
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
MEM0_API_KEY=
```

If `MEM0_API_KEY` is empty, the memory adapter uses the local fallback path,
which is fine for early testing but weaker than persistent hosted memory.

## 4. Install Kaizen on EC2

Clone the repo to `/opt/kaizen/habitbot` and run the bootstrap:

```bash
sudo mkdir -p /opt/kaizen
sudo chown -R ubuntu:ubuntu /opt/kaizen
git clone <repo-url> /opt/kaizen/habitbot
cd /opt/kaizen/habitbot
bash scripts/aws-ec2-bootstrap.sh
```

The bootstrap runs:

- dependency install with `uv`
- Mini App production build
- Alembic migrations, including `CREATE EXTENSION IF NOT EXISTS vector`
- idempotent RAG corpus embedding load
- systemd service install and restart

Useful service commands:

```bash
sudo systemctl status kaizen
sudo journalctl -u kaizen -f
sudo systemctl restart kaizen
```

The provided systemd unit assumes the default Ubuntu EC2 user and the repository
path `/opt/kaizen/habitbot`. If you use a different user or path, update
`deploy/aws/kaizen.service` before running the bootstrap.

## 5. Configure Nginx and TLS

On EC2, copy the Nginx example and replace `kaizen.example.com` with your real
domain:

```bash
sudo cp deploy/aws/nginx.conf.example /etc/nginx/sites-available/kaizen
sudo ln -s /etc/nginx/sites-available/kaizen /etc/nginx/sites-enabled/kaizen
sudo nginx -t
sudo systemctl reload nginx
```

Install Certbot and issue the certificate:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d kaizen.example.com
```

## 6. Confirm the Deploy

```bash
curl https://kaizen.example.com/health
```

Expected response:

```json
{"status":"ok"}
```

Also open `https://kaizen.example.com/miniapp`. It should return the built Mini
App instead of `503`.

## 7. Register Telegram

Register the webhook with the same `TELEGRAM_WEBHOOK_SECRET` stored in
`/opt/kaizen/.env`:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook" \
  -d "url=<PUBLIC_URL>/webhook" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

Telegram sends that value back as `X-Telegram-Bot-Api-Secret-Token`; Kaizen
rejects webhook calls without it.

In BotFather, set the Mini App domain to the public HTTPS host. Then restart the
service so startup registers the bot menu button using `PUBLIC_URL`:

```bash
sudo systemctl restart kaizen
```

## 8. Smoke Test

1. Send `/start` to the bot from the allowed Telegram account.
2. Confirm the reply contains an `Open Dashboard` Mini App button.
3. Send a normal `log`, such as `read for 20 minutes and went to the gym`.
4. Confirm the bot replies and `logs` has a new row in RDS.
5. Open the dashboard from Telegram and confirm the recent log appears.

If `/start` says the dashboard is not configured, set `PUBLIC_URL` in
`/opt/kaizen/.env` and restart `kaizen`.

Keep only one running Kaizen web process while the scheduler is in-process;
running multiple app instances would make multiple schedulers eligible to fire.
