# Bug: logs ignore user-stated date; always attributed to submission time

Date: 2026-07-04 (DONE)

## Summary

When a user writes a log like "completed running on 3rd Jan" on 4th January, the
system records it as a 4th January log. The natural-language date in the message
is completely ignored — the LLM extraction schema has no date field, the intake
path never parses a date from text, and the `Log` model has only a server-side
`created_at` timestamp with no `logged_date` column. All downstream date-scoped
queries (evidence ledger, streaks, agent context, dashboard) key off
`Log.created_at`, so every subsystem inherits the wrong date.

## Observed behavior

1. User sends `"completed running on 3rd Jan"` on 2026-01-04 at 10:00am.
2. `Log` row stores `created_at = 2026-01-04 10:00` and `text = "completed running on 3rd Jan"`.
3. `ExtractedFacts` has no date field — the LLM never extracts `2026-01-03`.
4. The evidence ledger (`app/habits/evidence.py:95`) computes `target_date = _app_date(log.created_at)` → `2026-01-04`.
5. Running shows as completed on the 4th, missing on the 3rd.

## Expected behavior

The LLM extractor should parse the date from the user's natural language and the
system should attribute the log to the stated date. If no date is mentioned, the
system defaults to the current date (today).

## Root cause

### Layer 1: `ExtractedFacts` schema has no date field

`app/extract/schema.py` defines `habits`, `adherence`, `mood`, `trigger`, and
`context` — but no `date` or `logged_date` field. The LLM prompt in
`app/extract/extractor.py` never asks the model to extract a date.

### Layer 2: Intake only uses `func.now()` for date assignment

`app/telegram/intake.py:_handle_log_message` creates the `Log` row with only
`telegram_user_id` and `text`. `Log.created_at` defaults to `func.now()`. There
is no code path that sets a date from the extracted facts.

### Layer 3: `Log` model has no `logged_date` column

`app/db/models.py:26-30` — the `Log` table has `created_at` but no
`logged_date`. Without this column, there is nowhere to persist the parsed date
even if extraction returned one.

### Layer 4: All date-scoped queries key off `Log.created_at`

Every subsystem that needs "which day does this log belong to" uses
`Log.created_at` directly:

| File | Line(s) | Usage |
|---|---|---|
| `app/habits/evidence.py` | 95 | `target_date = _app_date(log.created_at)` |
| `app/habits/evidence.py` | 279-281 | `Log.created_at >= _day_start(start_date) ... < _day_start(end_date)` |
| `app/gamification/xp.py` | 45-50 | Streak check: `Log.created_at >= day_start AND < day_end` |
| `app/agent/runner.py` | 53-54 | Today's logs: `Log.created_at >= day_start AND < day_end` |
| `app/dashboard.py` | 154, 163 | Recent logs ordered by `desc(Log.created_at)` and display it |
| `app/memory/store.py` | ~7-17 | Mem0 storage text has no date |

## Impact

- **High severity**: habit-state for any log with an explicit past/future date
  is wrong. This affects:
  - Whether a habit shows as done/missing on the correct calendar day
  - Streak calculations (gaps appear where there shouldn't be)
  - XP awarded to the wrong day
  - Dashboard and agent replies attribute accomplishments to the wrong date
  - Memory recall has no day-boundary awareness (compounds the existing
    `2026-07-04-memory-day-boundary-blindness.md` bug)

## Suggested fix

### Step 1: Add `logged_date` column to `Log` model

New nullable `Date` column `logged_date` on the `logs` table via Alembic
migration. When NULL, it means "use created_at date" (backward compatible).

### Step 2: Have the LLM extract the date as part of structured output

Add `logged_date: date | None` to `ExtractedFacts` in `app/extract/schema.py`.
Update the system prompt in `app/extract/extractor.py` to include
`"Current date: YYYY-MM-DD"` so the LLM can resolve phrases like "on 3rd Jan",
"yesterday", "last Tuesday". If no date is mentioned in the text, the LLM
returns `null` and the system falls back to today.

No separate date-parsing library needed — the existing extraction LLM call
already handles this. The approach is consistent with how `habits`,
`adherence`, etc. are already extracted.

### Step 3: Set `log.logged_date` from extracted facts in intake

In `app/telegram/intake.py:_handle_log_message`, after extraction succeeds, set
`log.logged_date = facts.logged_date` (nullable — `None` means fallback to
`created_at` date).

### Step 4: Switch all date-scoped queries to `COALESCE(logged_date, created_at::date)`

Every query in the table above that uses `Log.created_at` for date assignment
or filtering must be updated. Use `COALESCE(Log.logged_date, Log.created_at::date)`
in SQL or the equivalent Python-level fallback `log.logged_date or _app_date(log.created_at)`.

### Step 5: Update `EffectiveLogEvidence` to carry the effective date

`app/habits/evidence.py:47` — `EffectiveLogEvidence` has `created_at` but
should also expose the resolved `effective_date` for consumers that need it.

### Step 6: Update tests

- `tests/telegram/test_intake.py` — add a test where explicit date text sets
  `logged_date` and the extracted facts carry the date
- `tests/habits/test_habit_state.py` — verify `logged_date` takes precedence
- `tests/test_dashboard.py` — verify dashboard shows correct dates
- `tests/extract/test_extractor.py` — verify the LLM extracts dates from text
  when present and returns `null` when absent

## Out of scope

- **Correction flow** (`app/corrections/service.py`): changing how corrections
  resolve target dates is a separate issue. The correction flow continues to
  use `Log.created_at` for now.
- Cross-timezone date handling beyond what `COALESCE` and the app timezone
  already provide.

## Dependencies

- Alembic migration adding `logged_date` to `logs`
- No new third-party dependencies — the existing LLM extraction already handles
  natural-language date parsing.
- This fix also partially mitigates `2026-07-04-memory-day-boundary-blindness.md`
  because logs with explicit dates will now be scoped to the correct day in the
  evidence ledger and agent context queries.

## Acceptance criteria

1. Sending `"completed running on 3rd Jan"` on Jan 4 sets `log.logged_date =
   2026-01-03` and habit state shows running as done on Jan 3, not Jan 4.
2. Sending `"went to the gym yesterday"` on Jan 4 sets `log.logged_date =
   2026-01-03`.
3. Sending `"read a book"` (no date) on Jan 4 leaves `log.logged_date = NULL`
   and habit state correctly attributes it to Jan 4 (fallback to `created_at`).
4. Streak queries, dashboard, agent "today's logs", and evidence ledger all
   respect `logged_date` when present.
5. `uv run pytest` passes.
6. `uv run ruff check .` is clean.
