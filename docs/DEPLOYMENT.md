# Deployment: Oracle Cloud + Supabase

Production shape:

- **Supabase** hosts PostgreSQL + pgvector: logs, facts, habit state,
  interventions, RAG corpus embeddings, and Mem0 memories.
- **Oracle Cloud Always Free VM** runs FastAPI, the in-process scheduler, and
  Caddy (automatic HTTPS) in front of Uvicorn.
- Telegram and iPhone Shortcuts post to `https://<host>/webhook`.

The code side is done. The steps below need your accounts, so they are yours to
run. Do them in order; each ends with a check.

## Decisions already made

| Question | Decision | Why |
|---|---|---|
| Region | Supabase `ap-southeast-1` (Singapore) and Oracle's Singapore region | Matches `APP_TIMEZONE`; same region keeps DB round-trips in single-digit ms. Oracle's home region is fixed at signup, so if yours isn't Singapore, pick the Supabase region closest to it. |
| Which Supabase connection | **Session pooler**, port 5432 | The direct host is IPv6-only (Oracle VCNs default to IPv4). The transaction pooler (6543) breaks asyncpg prepared statements. |
| Domain | `<public-ip-with-dashes>.sslip.io` | Free, no DNS setup, and Let's Encrypt accepts it. Swap for a real domain any time by changing `KAIZEN_HOST` and `PUBLIC_URL`. |
| Mem0 | Self-hosted on Supabase pgvector (`MEM0_API_KEY` empty) | Keeps memories in your own DB with no extra third party. Hosted Mem0 memories are not migrated; memory starts fresh. |
| Supabase Data API | **Off** | The app connects to Postgres directly. Leaving the REST API on would expose `public` tables to anyone holding the anon key. |
| Webhook registration | Automatic on startup when `PUBLIC_URL` is set | No manual `curl setWebhook`. |
| Supabase free-tier pausing | Not a concern | Projects pause after 7 days of no activity; scheduler ticks hit the DB three times a day. |

## 1. Supabase

1. Create a project at <https://supabase.com/dashboard>: region Singapore, and a
   strong DB password you save in a password manager.
2. **Project Settings → Data API**: turn the Data API off.
3. **Connect** (top bar) → **Session pooler** → copy the URI. It looks like
   `postgresql://postgres.<ref>:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`.
4. Fill in the password and append `?sslmode=require`. URL-encode special
   characters in the password (`@` → `%40`, `#` → `%23`, `/` → `%2F`).
   That string is your `DATABASE_URL`.

No manual SQL is needed: the first migration runs
`CREATE EXTENSION IF NOT EXISTS vector`, and Mem0 creates its own table.

**Check:** from your laptop, run
`DATABASE_URL='<url>' uv run alembic upgrade head`. It should print every
migration with no error. (Or let the VM do it in step 3.)

**Optional, if you have data on the old AWS RDS:**

```bash
pg_dump --no-owner --no-acl -Fc "<old RDS url>" -f kaizen.dump
pg_restore --no-owner --no-acl -d "<supabase session pooler url>" kaizen.dump
```

Do this instead of running `alembic upgrade head` on an empty database, then
run `alembic upgrade head` afterwards to apply any newer migrations.

## 2. Oracle VM

1. **Upgrade the account to Pay As You Go** (Billing → Upgrade). Always Free
   resources stay $0, and Oracle stops reclaiming "idle" free VMs, which a
   mostly idle bot would otherwise be. Set a budget alert of $1 while you're
   there.
2. **Compute → Instances → Create**:
   - Image: Canonical Ubuntu 24.04
   - Shape: `VM.Standard.A1.Flex` (Ampere ARM), 1 OCPU / 6 GB is plenty
     (Always Free allows up to 4 / 24)
   - Networking: create a new VCN with a public subnet, and assign a public IPv4
     address
   - Add your SSH public key
   - If you get "Out of capacity", try another availability domain or retry
     later. The x86 `VM.Standard.E2.1.Micro` also works but only has 1 GB RAM.
3. **Networking → VCN → Security Lists → Default**: add ingress rules for
   TCP **80** and **443** from `0.0.0.0/0`. (The bootstrap script opens the same
   ports in the VM's own iptables.)
4. Note the public IP, e.g. `140.245.1.2` → host `140-245-1-2.sslip.io`.

**Check:** `ssh ubuntu@<ip>` works.

## 3. Install Kaizen on the VM

```bash
ssh ubuntu@<ip>
sudo mkdir -p /opt/kaizen && sudo chown ubuntu:ubuntu /opt/kaizen
git clone <your repo url> /opt/kaizen/app
```

If the repo is private, first create a deploy key: `ssh-keygen -t ed25519` on the
VM, then add `~/.ssh/id_ed25519.pub` under GitHub repo → Settings → Deploy keys
(read-only), and clone with the `git@github.com:` URL.

Create `/opt/kaizen/.env` from `.env.example` (`nano /opt/kaizen/.env`, then
`chmod 600 /opt/kaizen/.env`):

| Key | Value |
|---|---|
| `TELEGRAM_TOKEN` | from BotFather (same bot as before) |
| `ALLOWED_USER_ID` | your Telegram user ID |
| `TELEGRAM_WEBHOOK_SECRET` | new random value: `openssl rand -hex 32` |
| `DATABASE_URL` | Supabase session pooler URL from step 1 |
| `LLM_API_KEY`, `EMBED_API_KEY` | same as local |
| `LLM_MODEL` | leave empty to use the default, or set explicitly |
| `LANGFUSE_*` | same as local |
| `PUBLIC_URL` | `https://140-245-1-2.sslip.io` (no trailing slash) |
| `SCHEDULER_SECRET` | `openssl rand -hex 32` |
| `MEM0_API_KEY` | **leave empty** |
| `APP_TIMEZONE` | `Asia/Singapore` |

Then run:

```bash
cd /opt/kaizen/app
KAIZEN_HOST=140-245-1-2.sslip.io bash scripts/oracle-bootstrap.sh
```

This installs Caddy and uv, opens ports 80/443, installs the systemd units, and
runs `scripts/deploy.sh` (dependency sync → migrations → corpus embedding →
restart). uv downloads Python 3.12 itself.

**Check:**

- The script ends with `{"status":"ok"} kaizen is up`.
- `curl https://140-245-1-2.sslip.io/health` from your laptop returns
  `{"status":"ok"}`. The first request may take ~10 s while Caddy gets the
  certificate.
- `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"` shows your URL and
  no `last_error_message`.
- Send the bot `/start`, and then a log like "did gym".

## 4. Retire AWS

When the bot works on Oracle, terminate the EC2 instance and delete the RDS
instance, any snapshots, and any Elastic IPs so billing stops. Your local
`.env.production` still points at EC2; update or delete it.

## 5. iPhone Shortcuts

Point every Shortcut that posts to the old EC2 URL at the new `PUBLIC_URL`.

## Day-to-day operations

| Task | Command (on the VM) |
|---|---|
| Ship a new version | `bash /opt/kaizen/app/scripts/deploy.sh` |
| Logs | `journalctl -u kaizen -f` |
| Restart | `sudo systemctl restart kaizen` |
| Manual proactive tick | `curl -X POST -H "X-Scheduler-Secret: $SECRET" http://127.0.0.1:8000/scheduler/tick` |

Backups: the Supabase free plan has no downloadable backups. For a nightly
dump on the VM, install a `postgresql-client` at least as new as your Supabase
Postgres version (Settings → Infrastructure shows it; Ubuntu's default client may
be older, so use the PGDG apt repo). Then add this line with `crontab -e`:

```
0 3 * * * pg_dump "$(grep ^DATABASE_URL= /opt/kaizen/.env | cut -d= -f2-)" -Fc -f /opt/kaizen/backup-$(date +\%a).dump
```

That keeps a rolling 7 days of dumps.

## Later: Google Sheets and Google Health

These are build-order steps 4 and 5 in `docs/DIRECTION.md`. They aren't
implemented yet, so nothing is needed now. When you build them, you'll need:

- **Sheets:** a Google Cloud project with the Sheets API enabled, a service
  account with a JSON key, and the target sheet shared with the service
  account's email as Editor.
- **Google Health:** an OAuth client in the same project with the Google Health
  API enabled, and a one-time consent flow to get a refresh token.

Keys go in `/opt/kaizen/.env`, and new settings get added to `.env.example`.
