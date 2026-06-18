Milestone 0 — Lock the product contract

Goal: Stop scope drift before coding too much.

You already have the core PRD, but the review highlights four missing pieces that should become explicit requirements:

Onboarding
How does the user create the first habit plan?
Can Kaizen infer cadence, aliases, triggers, evidence windows, and success condition from chat?
Does it ask for confirmation before saving?
Correction loop
User can say:
“Count this for gym.”
“Undo that.”
“That was a slip, not a success.”
“Don’t use this as evidence next time.”
This is important because your extraction is intentionally conservative.
Intervention policy
Define when Kaizen nudges, checks in, or stays silent.
Include quiet hours, daily cap, confidence threshold, abstain reasons, and rationale logging.
Privacy contract
Retention.
Export.
Deletion.
Memory clearing.
Sensitive-topic handling.

Deliverable: Update docs/CONTEXT.md and PRD sections before implementation goes too far.

Done when: Someone reading the repo knows exactly what Kaizen will and will not do in v1.

Milestone 1 — Core Telegram logging loop

Goal: Make the simplest useful version work inside Telegram.

Build this first:

Telegram message
→ webhook verification
→ allowed user check
→ persist raw log
→ do not store commands as logs
→ basic reply

Required pieces:

FastAPI webhook route.
ALLOWED_USER_ID enforcement.
Telegram secret verification.
/start
/dashboard
/app
raw logs table.
basic local/dev setup.

Do not overbuild the agent yet. This milestone proves the app can receive real life input reliably.

Deliverable: You can message your bot:

rough day, skipped gym, doomscrolled until 2am

And Kaizen stores it as a log.

Done when: Logs are persisted correctly and commands are excluded.

Milestone 2 — Habit plan model

Goal: Define what Kaizen is trying to detect.

Before extraction, you need the structured target.

Tables/models should include:

habits
- id
- name
- cadence_type
- cadence_config
- success_condition
- aliases
- known_triggers
- expected_evidence_window
- goal
- active

For v1, support only:

daily
specific weekdays
N times per week

Also create seed habit plans manually first. Do not start with fancy onboarding unless you want to slow yourself down.

Example habit:

{
  "name": "Gym",
  "cadence_type": "times_per_week",
  "cadence_config": { "times": 3 },
  "success_condition": "Completed a gym workout or meaningful strength session",
  "aliases": ["gym", "workout", "pull day", "push day", "leg day"],
  "known_triggers": ["tired after school", "late night", "rain"],
  "expected_evidence_window": "same_day"
}

Deliverable: A user can have persisted habits with cadence and matching metadata.

Done when: Dashboard/backend can know what habits are due today, even before AI extraction exists.

Milestone 3 — Structured extraction v1

Goal: Turn messy natural language into typed evidence.

This is the first truly load-bearing AI milestone.

Flow:

raw log
→ LLM extraction via app/llm/client.py
→ Pydantic validation
→ extracted facts
→ candidate habit evidence
→ store result

Important: follow your PRD rule strictly.

No regex parsing of model free text.
No vendor SDK imports outside app/llm/client.py.
Use Pydantic v2 schemas.

Example extraction schema:

class ExtractedFact(BaseModel):
    type: Literal["habit_evidence", "mood", "sleep", "trigger", "obstacle", "reflection"]
    text: str
    confidence: float
    occurred_at: date | None

class HabitEvidence(BaseModel):
    habit_id: UUID
    status: Literal["success", "miss", "partial", "ambiguous"]
    evidence_text: str
    confidence: float
    reason: str

Core rule:

If ambiguous, leave unmatched.

For example:

"rough day, skipped gym, doomscrolled until 2am"

Should probably produce:

Gym: miss
Sleep / screen habit: likely miss, if such habit exists
Mood: rough day
Trigger: doomscrolling / late night

But something like:

"walked around a bit"

Should not automatically count as exercise unless the success condition says it should.

Deliverable: Logs generate validated extracted facts and habit evidence.

Done when: You can inspect DB rows and see conservative, explainable habit matches.

Milestone 4 — Habit state engine

Goal: Derive actual habit status from persisted data, not React inference.

This is where Kaizen starts feeling like a habit app.

Build backend read models:

today's habit state
weekly habit state
recent logs
recent evidence
missed habits
streak-ish progress
XP/level summary

The dashboard should only display backend-derived state.

Do not let the frontend infer:

“if there is a log containing gym, mark gym complete”

Nope. Tiny goblin logic. Backend owns truth.

Deliverable: Telegram Mini App can show:

today’s habits
completed/missed/unknown
recent logs
recent extracted facts
recent interventions

Done when: The dashboard reflects the same state your backend would use for nudges.

Milestone 5 — Correction loop

Goal: Let the user repair Kaizen’s interpretation.

Do this before proactive nudges. Otherwise your bot will eventually annoy you with wrong assumptions.

Support chat commands or natural language:

count that as gym
undo gym credit for today
mark sleep as missed
that was not a workout

Implementation:

user correction
→ resolve target log/habit/date
→ create correction record
→ recompute habit state

You need a corrections or evidence_overrides table.

Example:

habit_evidence_overrides
- id
- log_id nullable
- habit_id
- date
- override_status
- user_text
- reason
- created_at

This is a major trust feature. The PRD review specifically warns that conservative matching creates a product tax: sometimes Kaizen will fail to give deserved credit, so the user needs fast repair.

Deliverable: User can correct false positives and false negatives in Telegram.

Done when: Habit state changes after correction, and the correction is auditable.

Milestone 6 — Grounded coaching/RAG

Goal: Make advice technique-grounded, not generic “you got this bro” fluff.

Build:

behavioral science corpus
→ chunk
→ embed
→ store in pgvector
→ retrieve
→ rerank
→ generate response naming technique

Your corpus should be curated and small at first.

Example techniques:

implementation intentions
habit stacking
stimulus control
self-monitoring
temptation bundling
friction reduction
coping planning
identity-based habits
recovery planning
WOOP / mental contrasting

The answer should look like:

Technique: Implementation intention

You usually slip on gym after late nights. For tomorrow, use a specific if-then:
“If I reach home before 7:30pm, I go straight to the gym before dinner. If I reach home after 7:30pm, I do a 15-minute fallback workout.”

Deliverable: Reflection questions use both user history and retrieved technique chunks.

Done when: Kaizen can answer:

how did this week go?
when do I usually slip?
what should I do tomorrow?

Using actual logs, not vibes.

Milestone 7 — Memory and reflection

Goal: Make Kaizen remember patterns compactly.

Do not dump all logs into context.

Create memory summaries such as:

User often misses gym after late sleep.
Doomscrolling is commonly mentioned after stressful days.
User responds better to small fallback plans than motivational pressure.

Memory types:

pattern
preference
trigger
successful_strategy
recurring_obstacle

Flow:

new extracted facts
→ update memory selectively
→ recall compact memory for reflections/interventions

Deliverable: Kaizen can answer historical questions without loading every log.

Done when: Reflections mention stable patterns backed by recent evidence.

Milestone 8 — Scheduled fallback check-ins

Goal: Add non-agentic scheduled accountability first.

Before “smart proactive nudges,” start with predictable due-habit checks.

Example:

If gym is due today and no evidence exists by expected window,
send fallback check-in unless quiet hours/daily cap block it.

This is simpler than full proactivity and easier to test.

You need:

scheduler tick
→ due habit check
→ quiet hours check
→ daily cap check
→ intervention record
→ send or record silence

Intervention table:

interventions
- id
- type: check_in | nudge | silence
- habit_id nullable
- message
- rationale
- decision_inputs
- sent_at nullable
- created_at

Deliverable: Kaizen sends basic check-ins when expected evidence is missing.

Done when: Every send or non-send is recorded.

Milestone 9 — Proactive nudge agent

Goal: Let Kaizen decide whether a timely nudge is useful.

Only do this after you have:

logs
extracted facts
habit state
corrections
memory
intervention logging

Decision inputs should include:

due status
recent misses
recent streak
emotional load
sleep-risk mentions
known trigger active
last intervention time
daily cap
quiet hours
confidence in evidence
user engagement with previous nudges

Decision outputs should be typed:

class NudgeDecision(BaseModel):
    action: Literal["send_nudge", "send_check_in", "stay_silent"]
    confidence: float
    rationale: str
    habit_id: UUID | None
    technique_name: str | None
    message: str | None
    abstain_reason: str | None

This is where LangGraph becomes useful:

scheduled tick
→ load habit state
→ recall memory
→ retrieve technique
→ decide
→ validate decision
→ send or stay silent
→ trace

Deliverable: Kaizen sometimes nudges, but often stays silent.

Done when: You can inspect why each decision happened.

Milestone 10 — Observability and evals

Goal: Make this credible as an AI engineering case study.

Add Langfuse tracing around:

extraction
embedding
retrieval
reranking
response generation
nudge decision

Track:

latency
tokens
cost
model
prompt version
output schema validity

Evals:

Extraction eval
hand-labeled logs
expected habit matches
expected misses
ambiguous cases
Grounding eval
does reply name a real technique?
is technique relevant?
does it use user context correctly?
Proactivity eval
should send vs stay silent
quiet hours respected
daily cap respected
rationale quality
Regression tests
commands not stored as logs
unauthorized users rejected
habit state computed correctly
correction overrides work

Deliverable: evals/ folder and CI tests.

Done when: You can show measurable quality, not just screenshots.

Milestone 11 — Deployment

Goal: Make it usable daily.

Given your earlier direction, a solid learning-oriented deployment is:

EC2
→ FastAPI + scheduler + built Mini App
RDS PostgreSQL
→ logs, habits, memory, interventions, pgvector
Nginx
→ HTTPS reverse proxy
systemd
→ keep app running

For v1, app-local scheduler is fine.

But make sure you have:

HTTPS.
Telegram webhook set.
environment variables.
Alembic migrations.
backups or at least export.
billing alerts.
logging.
restart policy.

Deliverable: You can use Kaizen every day from Telegram without your Mac running.

Done when: You have 7 days of real logs in production.

Suggested milestone order

This is the order I’d actually build:

0. Product contract hardening
1. Telegram logging loop
2. Habit plan model
3. Structured extraction
4. Habit state engine
5. Correction loop
6. Dashboard read models + Mini App
7. RAG grounded coaching
8. Memory + reflection
9. Scheduled fallback check-ins
10. Proactive nudge agent
11. Observability + evals
12. Deployment hardening

Slight adjustment: if you already have deployment partially done, keep it alive, but don’t sink too much time into AWS polish before extraction/correction works.

The real MVP

Your true MVP is not:

Telegram bot + dashboard + streaks

That’s crowded.

Your true MVP is:

I can write messy daily logs in Telegram.
Kaizen conservatively understands what happened.
It updates my habit state.
When I ask for reflection, it uses my actual history.
When it gives advice, it names a behavioral technique.
When it is unsure, it asks or stays silent.
When it is wrong, I can correct it.

That is the wedge.

What to build next, specifically

From where you are now, I’d do this next:

Next 3 milestones
Priority	Milestone	Why
1	Telegram logging + raw persistence	Gives you real data quickly
2	Habit plan + structured extraction	This is the core AI judgment loop
3	Correction loop	Prevents trust collapse when the AI misreads logs

Do not start with XP, levels, fancy dashboard UI, or overly complex agents.

Those are toppings. The burger is extraction, habit state, correction, and grounded reflection.