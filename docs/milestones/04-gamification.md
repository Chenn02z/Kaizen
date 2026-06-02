# Milestone 4 — Gamification & Telegram Mini App

**Goal:** Turn habit adherence into an RPG progression system — XP, levels,
per-habit skill tracks — and surface it as a visual character sheet inside
Telegram via a Mini App.

**Unlocks:** user retention mechanic; resume keywords Telegram Mini App, Web App
SDK, gamification, XP system.

**Owner subagent:** `backend-engineer` (XP logic + API routes + Mini App HTML)

## Scope

In: a `user_progress` table (XP, level) and `habit_progress` table (per-habit
XP/level), XP award logic wired into the extraction flow, a bot reply that
reports XP gain and level-ups, a FastAPI route serving the Mini App HTML, and a
Telegram menu button pointing to it.

Out: memory/longitudinal reasoning (m5), proactive behaviour (m6).

## Prerequisites

Milestone 2 (extracted facts supply the adherence signal).

## XP rules

| Adherence | XP per habit mentioned |
|-----------|----------------------|
| `yes`     | 50 XP                |
| `partial` | 20 XP                |
| `no`      | 0 XP                 |

**Level thresholds:** level N is reached at `100 × (N-1)²` cumulative XP
(level 1 = 0 XP, level 2 = 100 XP, level 3 = 400 XP, level 4 = 900 XP, …).
Formula: `level = floor(sqrt(xp / 100)) + 1`.

**Streak bonus:** if the user logged adherence `yes` or `partial` on each of the
last 3 consecutive calendar days, award an extra 10 XP per session (checked at
award time from the `extracted_facts` table).

## Tasks

- [ ] `user_progress` table: `xp` (int), `level` (int), `updated_at`.
      One row per user (keyed on `telegram_user_id`). Migration.
- [ ] `habit_progress` table: `telegram_user_id`, `habit_name`, `xp`, `level`.
      One row per (user, habit). Migration.
- [ ] `app/gamification/xp.py`: `award_xp(facts, telegram_user_id)` — awards
      XP to both tables, recalculates levels, returns `XPResult` (Pydantic:
      xp_gained, new_total_xp, old_level, new_level, levelled_up bool).
- [ ] Wire `award_xp` into the webhook after successful extraction.
- [ ] Bot reply appended with XP summary: `"+70 XP · Level 3 🗡️"`. Level-up
      gets its own line: `"⬆️ LEVEL UP — you are now Level 4!"`.
- [ ] `GET /me` JSON endpoint: returns `UserStats` Pydantic model (level, xp,
      xp_to_next_level, habits: list of {name, level, xp}).
- [ ] `GET /miniapp` route: serves the Mini App HTML page (single file, inline
      CSS/JS, Telegram Web App SDK script tag). The page fetches `/me` and
      renders the character sheet: overall level bar, per-habit skill rows.
- [ ] Register the Mini App URL as the bot's menu button via the Telegram API
      on startup (`setChatMenuButton` — call once in `app/main.py` lifespan).

## Acceptance criteria (verify each)

- `yes` adherence awards 50 XP per habit; `partial` awards 20; `no` awards 0
  → unit test in `tests/gamification/test_xp.py`.
- XP accumulates across calls and triggers `levelled_up=True` at the correct
  threshold → test crossing level 1→2 boundary (needs 400 XP total).
- Streak bonus of 10 XP fires when the last 3 days all have `yes`/`partial`
  → test with mocked `extracted_facts` rows.
- `GET /me` returns valid `UserStats` JSON with correct values after a sequence
  of awards → test via the ASGI test client.
- `GET /miniapp` returns 200 and the response body contains the Telegram Web
  App SDK script tag → test.

## Definition of done

Acceptance criteria tested, lint clean, `code-reviewer` run, diff surgical.

## Resume bullet unlocked

Built a Telegram Mini App with an RPG XP/levelling system driven by real
habit-adherence data, served from the same FastAPI backend.
