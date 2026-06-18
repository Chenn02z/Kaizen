# Milestone 10 - Lesson-grounded reflection

**Goal:** Make reflection answers and proactive nudges use the user's own
lesson corpus when the user asks what to change, while still grounding every
answer in actual habit history.

**Unlocks:** the product's sharper voice: Kaizen applies lessons the builder
has personally distilled from books and experience instead of sounding like a
generic habit coach.

**Owner subagent:** `rag-engineer` with agent and eval support.

## Scope

In: a normalized lesson-note corpus format, lesson retrieval for
action-oriented `reflection question`s, lesson retrieval for proactive ticks
based on due habits and recent drift, and evals that prove lesson use is
relevant rather than decorative.

Out: book summarization, copied source passages, arbitrary book Q&A, a daily
"lesson of the day" broadcast, habit editing, and new third-party content
sources.

## Prerequisites

Milestones 3, 5, 6, 8, and 9. Milestone 9 is included because proactive lesson
use should rely on corrected habit state before it is trusted for daily nudges.

## Product decisions

- The corpus is a set of `lesson` notes written in the builder's own words.
- Each lesson maps to one or more `technique`s. The lesson gives Kaizen
  application judgment; the technique gives the grounded behavioral method.
- Reflection remains history-first. Kaizen should retrieve lessons only after it
  has identified the relevant habit pattern, trigger, or question intent.
- Proactive ticks must not send generic educational content. They may retrieve a
  lesson only when the due-habit state, recent history, and intervention policy
  indicate that a nudge may be useful.
- If no retrieved lesson fits the user's situation, Kaizen should answer from
  history or stay silent rather than forcing a technique.

## Lesson format

Each corpus entry should be inspectable as a self-contained note:

- `source`: book, article, course, or personal experience label.
- `technique`: one or more canonical technique names.
- `lesson`: the core idea in the builder's own words.
- `use_when`: situations where the lesson fits.
- `avoid_when`: situations where the lesson would be wrong or tone-deaf.
- `example_application`: one concrete habit-context example.

Markdown is acceptable if tests can parse or inspect the required sections.
Only add database columns or migrations if the implementation needs structured
metadata beyond the existing `corpus_chunks` table.

## Reflection behavior

Reflection questions split into two useful modes:

- Descriptive reflection: "how did this week go?", "when do I usually skip gym?"
  These answers must primarily use logs, extracted facts, habit state, and
  memory.
- Coaching reflection: "what should I change tomorrow?", "how do I stop
  doomscrolling after bad days?" These answers must use history plus retrieved
  lessons, name the technique, and explain why the lesson fits this user's
  pattern.

## Proactive behavior

Scheduled ticks should retrieve lessons from a query built from concrete state:

- due or drifting habit
- recent misses or partials
- known triggers
- memory patterns
- last intervention reason when relevant

The query must not fall back to a generic phrase such as "behavior change habit"
when real state is available.

## Tasks

- [ ] Normalize current `corpus/` files into lesson notes with the required
      sections while keeping them self-authored.
- [ ] Add or update corpus integrity tests so required lesson sections are
      present and every lesson maps to at least one technique.
- [ ] Update reflection routing so action-oriented reflection questions retrieve
      relevant lessons after recalling history.
- [ ] Update proactive tick retrieval so lesson queries are based on due habit
      state, recent drift, and memory rather than generic text.
- [ ] Update prompts so answers name the technique, apply one retrieved lesson,
      and connect it to the user's own history.
- [ ] Add eval scenarios for descriptive reflection, coaching reflection,
      irrelevant lesson abstention, and proactive lesson retrieval.

## Acceptance criteria (verify each)

- A coaching reflection such as "what should I change tomorrow?" retrieves at
  least one relevant lesson, names its technique, and ties the advice to a real
  recent pattern from the user's history.
- A descriptive reflection such as "when do I usually skip gym?" answers from
  logs/facts/memory and does not invent a lesson when no recommendation is
  requested.
- A proactive tick with a due habit and recent drift retrieves lessons using a
  query containing the habit and recent pattern, not a generic fallback query.
- If retrieved lessons do not fit the situation, the reply path either answers
  from history only or records a silence/abstain reason.
- Corpus integrity tests fail when a lesson is missing source, technique,
  lesson, use_when, avoid_when, or example_application.
- Judge evals include at least one scenario where lesson grounding improves the
  answer and one where forcing a lesson is penalized.
- `uv run pytest tests/rag tests/memory tests/agent tests/evals` passes, or a
  narrower equivalent test slice is documented with the reason.

## Definition of done

Acceptance criteria are covered by tests, `uv run ruff check .` is clean for
Python changes, and the corpus contains no copied source passages.

## Resume bullet unlocked

Extended RAG from generic technique retrieval to a self-authored lesson corpus
used for history-grounded reflection and proactive intervention decisions.
