# Bug: agent lacks day-boundary and time-of-day awareness in chat replies

Date: 2026-07-04 (DONE)

## Summary (two related gaps)

**Gap A — day-boundary blindness:** When the agent composes a chat reply, the
memory history it retrieves from Mem0 has no day-boundary awareness. A gym log
from 10pm yesterday can appear in today's recall results and the LLM interprets
it as a same-day event. When the habit-state summary simultaneously reports gym
as "missing" today, the LLM resolves the conflict incorrectly — it assumes the
user did the activity but forgot to log it, rather than recognizing the
activity belongs to a different calendar day.

**Gap B — time-of-day blindness:** The agent status line says
`gym: status=missing` at 8am, 2pm, and 11pm identically. The LLM has no way to
know the day is young and the habit is still achievable. This creates premature
"you missed it" tone when the user still has hours before the evidence window
closes. The codebase *has* `expected_evidence_window` (default 20:00) but never
surfaces it to the agent prompt.

## Observed behavior

1. Day 1, 10:00pm: user sends "went to the gym" — extracted, stored in Mem0,
   habit state shows gym as `done` for Day 1.

2. Day 2, 10:00am: user sends an ordinary chat message. The agent replies as if
   the user has been to the gym recently but did not log it as a habit today.

The reply is factually wrong: the user did log it correctly; the log simply
belongs to yesterday. The agent also treats 10am `missing` as if the day is
already lost.

## Expected behavior

- Day-boundary: when forming a reply on Day 2, the agent should recognize that
  yesterday's gym session is yesterday's evidence and today's gym is genuinely
  missing. It should not claim that a log is missing when in fact it was
  submitted.
- Time-of-day: at 10am, for a habit with a 20:00 window, the agent should
  acknowledge that the user still has time. Tone should be encouraging ("you
  still have until 8pm") rather than failure-oriented ("you missed it").

---

## Root cause: Gap A (day-boundary blindness)

### Layer 1: `app/memory/store.py::_facts_to_text` omits timestamps

Memories stored into Mem0 contain the log text, habit names, adherence, mood,
trigger, and context — but **no creation date or day label**. Example stored
string:

```
User log: went to the gym at 10pm. Habits mentioned: gym. Adherence: yes. Mood: good.
```

Without an embedded date, the semantic text is permanently ambiguous about which
day it refers to.

**Relevant code:** `app/memory/store.py:7-17` (`_facts_to_text`)

### Layer 2: `app/memory/recall.py::recall_history` strips Mem0 metadata

Mem0's `search` and `get_all` APIs return entries that include `created_at`,
`updated_at`, and other metadata alongside the `memory` text. But
`recall_history` extracts only `e["memory"]` and discards everything else:

```python
# app/memory/recall.py:7
return "\n".join(e["memory"] for e in entries if "memory" in e)
```

Even if the storage layer embedded a date, the recall layer would still collapse
memories from different days into an undated block of text passed to the LLM.

**Relevant code:** `app/memory/recall.py:5-7` (`recall_history`),
`app/memory/recall.py:11-13` (`detect_patterns`)

### Layer 3: No DB-level "today's logs" query supplements memory recall

The agent's only source of behavioral history for chat replies is Mem0 semantic
search — there is no query against the `logs` table to surface what was (or
wasn't) logged today. The `habit_state_summary` correctly reports `missing`
status per the evidence ledger, but the LLM can't cross-reference this against
concrete log text because it never sees today's actual logs.

**Relevant code:** `app/agent/graph.py:85-92` (`recall` node),
`app/agent/runner.py:40-65` (`run_user_message`)

### How the layers compound

```
Mem0 stores:  "went to gym at 10pm"    [no date — Layer 1]
Mem0 returns: "went to gym at 10pm"    [timestamp stripped — Layer 2]
Agent prompt: history = "went to gym at 10pm"
              habit_state = "gym: cadence=daily, status=missing"
                                            [no today's log text — Layer 3]
LLM resolves: "user went to gym but didn't log it"   ← wrong conclusion
```

---

## Root cause: Gap B (time-of-day blindness)

### The agent_status is binary — missing vs done

In `app/habits/state.py`, each habit has two status fields:

| Field | Purpose | At 8am | At 11pm |
|---|---|---|---|
| `day_status` | Frontend (3 states: done/missing/unknown) | `unknown` | `missing` |
| `agent_status` | Agent prompt (2 states: done/missing) | `missing` | `missing` |

`day_status` already has the concept of "not yet knowable" (returns `unknown`
before the evidence window), but `agent_status` collapses this to `missing`.
The agent prompt line reads:

```
- gym: cadence=daily, due_today=yes, status=missing
```

The `expected_evidence_window` (default 20:00) exists on `HabitPlanRead` but is
never exposed to the LLM. The LLM cannot distinguish "missing at 8am with 12
hours left" from "missing at 11pm with the day over."

**Relevant code:**
- `app/habits/state.py:182-184` (`agent_status` always "missing" when
  `cadence_due and not positive`)
- `app/habits/state.py:165-172` (`_format_agent_habit_line` — no window/passed
  fields)

---

## Suggested fix

Address all four layers:

### Fix 1: Layer 2 — Add relative date labels to recall output

In `recall_history`, extract `created_at` from Mem0 entries and prepend a
relative date label: `[today]`, `[yesterday]`, `[2 days ago]`, or the
human-readable date if older.

### Fix 2: Layer 3 — Query today's DB logs for agent context

In the agent graph `recall` node (or `run_user_message`), query the `logs`
table for today's log texts and pass them as a separate `today_logs` field.
The reply prompt should distinguish "today's submitted logs" from "historical
memory."

### Fix 3: Gap B — Add time-window fields to agent habit summary

In `_format_agent_habit_line`, add `window` and `window_passed` fields so the
agent line reads:

```
- gym: cadence=daily, due_today=yes, status=missing, window=20:00, window_passed=no
```

In `_build_habit_read_state`, set `agent_status` to `"pending"` (or keep
`missing` but add the window context) when the evidence window hasn't passed.
Alternatively, keep `agent_status = "missing"` but add the window/passed
fields as supplementary context — this is the lower-risk option.

### Fix 4: Add current time to the agent prompt

Add "Current time: HH:MM" to the system prompt so the LLM has calendar
awareness and can reason about time remaining.

---

## Impact

- The agent makes factually incorrect claims about what the user has or hasn't
  logged (Gap A).
- The agent panics about missed habits when the day has barely started (Gap B).
- Erodes trust: the user knows they logged gym yesterday and it's only 10am.
- Tone is failure-oriented instead of encouraging when there's still time.

## Acceptance criteria

**Gap A — day-boundary:**
- Day 1 10pm log "went to gym" → Day 2 10am chat reply does NOT claim the gym
  log is missing or unlogged.
- The agent can distinguish yesterday's memory from today's evidence.
- Regression test: two-day scenario where yesterday's gym log does not pollute
  today's reply about gym status.

**Gap B — time-of-day:**
- At 10am before the evidence window, the agent's tone acknowledges time
  remaining (e.g., "you still have until 8pm").
- `_format_agent_habit_line` includes `window` and `window_passed` fields.
- System prompt includes current time.

**General:**
- `habit_state_summary` still correctly reports gym as `missing` today — only the
  reply tone and context quality are fixed, not the habit tracking logic.
- `uv run pytest` passes.
