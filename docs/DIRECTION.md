# Kaizen Direction

Decided 2026-10-25. Kaizen refocuses on a fixed habit list fed by one-tap
buttons, short Telegram sentences, and device integrations. Freeform logging
stays as one input channel and as coach context.

## Habits

| Domain | Habit | Target | Input |
|---|---|---|---|
| Body | Gym | 3–4× / week | One-tap Shortcut button; logs the next split in the cycle PUSH → PULL → PUSH 2 → PULL 2 |
| Body | Run | 1× / week | One-tap Shortcut button |
| Body | Weigh-in | Mon / Wed / Fri / Sun | Shortcut reads latest weight from Apple Health (Hume syncs there) and posts it |
| Body | Sleep | Bed 23:30, wake 07:30, ±30 min is a hit | Google Health API (Fitbit Air) |
| Career | LeetCode | 1 / day | One Telegram sentence, parsed by the AI |
| Career | System design | Regular sessions | One Telegram sentence on the topic |
| Mind | Doomscrolling | < 15 social-app opens / day (tune after a week of baseline) | Shortcuts "App opened" automation for Instagram, X, TikTok, Reddit, YouTube |

Dropped: no-phone-for-30-min after waking. Revisit if open counts show mornings
are the problem.

## Behavior

- **Confirmations:** every log gets a one-line reply, e.g.
  "✅ PULL 2 logged, 3/4 this week". Reply to correct.
- **LeetCode parsing:** save immediately with whatever parsed (problem, pattern,
  difficulty, struggled). If a key field is missing, ask one optional follow-up;
  never block the log. No auto-detection via LeetCode's API.
- **Re-solve queue:** solved problems resurface at +3, +10, +30 days. Struggling
  on a re-solve resets the schedule.
- **Morning brief (08:00, once daily):** last night's sleep vs target,
  yesterday's social opens, today's gym split, one LeetCode pick (due re-solve
  first, else a weak-pattern problem), weekly progress (gym x/4, run x/1).
- **Nudges (max 2/day, besides the brief):**
  - Thu/Fri gym or run nudge when behind weekly pace.
  - Doomscroll nudge once when the daily cap is passed.
  - Missed weigh-in on a weigh-in day.
- **AI machinery:** Mem0 memory and freeform logs give the coach context. RAG
  technique tips appear only on drift (e.g. 2+ missed gym weeks).

## Dashboard

Google Sheets replaces the Mini App. The backend rewrites it nightly.

- `Weekly` tab: one row per week — gym x/4, run, weigh-ins, sleep hit %, avg
  social opens, LeetCode count.
- `Daily` tab: one row per day.

## New Third-Party Integrations

Approved: Google Health API, Google Sheets API. Apple Health and Shortcuts run
on-device and post to the existing webhook.

## Build Order

1. Habit model, gym/run buttons, confirmations
2. LeetCode parsing and re-solve queue
3. Morning brief
4. Sheets sync
5. Google Health sleep
6. Weight and social-open Shortcuts
7. Nudges
