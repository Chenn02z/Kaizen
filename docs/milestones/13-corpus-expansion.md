# Milestone 13 - Corpus expansion and retrieval sharpness

**Goal:** Expand Kaizen's self-authored `lesson` corpus from broad technique
notes into a larger set of situation-specific lessons, so retrieved advice fits
the user's actual `log`, history, trigger, and habit state instead of sounding
like generic habit coaching.

**Unlocks:** more reliable grounded coaching, stronger RAG eval signal, and a
clearer portfolio story for corpus design, retrieval quality, reranking, and
lesson application.

**Owner subagent:** `rag-engineer` with eval support.

## Scope

In: expanding `corpus/` to roughly 70-80 self-authored lesson chunks, adding
new behavioral-science perspectives that cover gaps in the current Atomic
Habits/Tiny Habits-heavy corpus, improving corpus metadata where needed,
updating fixed-query retrieval evals, and recording before/after retrieval and
reply-grounding numbers.

Out: copied book summaries, arbitrary book Q&A, clinical advice, scraping or
storing copyrighted passages, new external content APIs, frontend changes,
habit-plan editing, and a daily lesson broadcast.

## Prerequisites

Milestones 3, 7, 10, and 12. The current RAG pipeline, eval harness,
lesson-grounded reflection behavior, and habit-plan context should exist before
this milestone, because corpus expansion should be measured through the real
retrieval and reply paths.

## Product decisions

- The corpus remains a set of self-authored `lesson` notes, not source excerpts.
- Expansion should prioritize situation-specific chunks over more abstract
  technique definitions.
- Each new lesson should answer: "When this user situation appears, what should
  Kaizen try, and when would that advice be wrong?"
- New perspectives should broaden Kaizen's intervention judgment, not just add
  more labels for the same Atomic Habits/Tiny Habits ideas.
- Reranking remains part of the retrieval path. The milestone should prove
  whether a larger candidate set improves top result quality.
- If a retrieved lesson does not fit the user's actual context, Kaizen should
  abstain or answer from history rather than force a technique.

## Source mix

The implementation should start from the current 15 corpus entries, then add
new lesson cards from a controlled source mix:

- Atomic Habits and Tiny Habits refinements: concrete variants for gym, reading,
  sleep, doomscrolling, nutrition, partial completion, recovery, and forgotten
  cues.
- Wendy Wood / automaticity and context: lessons about habit automaticity,
  stable contexts, repetition, friction, and why intention alone fails.
- Motivational Interviewing: lessons about ambivalence, autonomy-respecting
  language, reflective responses, and avoiding preachy advice.
- Self-Determination Theory: lessons about autonomy, competence, relatedness,
  and why controlling pressure can backfire.
- ACT / psychological flexibility: lessons about urges, discomfort, values,
  self-criticism, and committed action despite difficult internal states.
- WOOP / mental contrasting: lessons about wish, outcome, obstacle, and plan for
  turning aspiration into a concrete obstacle plan.
- COM-B / Behaviour Change Wheel: diagnostic lessons that distinguish
  capability, opportunity, and motivation failures before choosing an
  intervention.

## Lesson format

Every lesson chunk should remain inspectable as plain markdown and include the
existing required fields:

- `source`
- `technique`
- `lesson`
- `use_when`
- `avoid_when`
- `example_application`

New or updated chunks should also include retrieval-oriented fields unless the
implementation documents a better equivalent:

- `situation_tags`: comma-separated tags such as `gym`, `late_work`,
  `doomscrolling`, `shame`, `low_motivation`, or `forgotten_cue`.
- `query_phrases`: natural-language phrases the user might actually write.
- `intervention_type`: one of `plan`, `shrink`, `environment`, `reflection`,
  `recovery`, `urge`, `motivation`, `diagnosis`, or `abstain`.

Structured metadata may be parsed from markdown at runtime or stored in the
existing `corpus_chunks.content`. Add database columns or migrations only if the
implementation needs queryable metadata beyond full-text lesson content.

## Target coverage

The expanded corpus should include at least:

- 70 self-authored lesson chunks total.
- 8 lessons for missed or partial exercise.
- 8 lessons for sleep, bedtime, and doomscrolling.
- 6 lessons for nutrition or snacking.
- 6 lessons for reading, learning, or project work.
- 8 lessons for relapse recovery, shame, and self-compassion.
- 8 lessons that focus on ambivalence, autonomy, or motivation quality rather
  than direct advice.
- 6 lessons that explicitly diagnose whether the failure is capability,
  opportunity, motivation, or an unclear goal.
- 5 lessons whose correct behavior is to avoid giving a technique-heavy answer
  and instead reflect, clarify, or abstain.

## Tasks

- [ ] Audit the current 15 corpus files and identify coverage gaps by habit
      domain, trigger, emotion, and intervention type.
- [ ] Add 55-65 new self-authored lesson chunks, preserving the required lesson
      format and avoiding copied source passages.
- [ ] Add `situation_tags`, `query_phrases`, and `intervention_type` to all
      corpus entries, including the existing files.
- [ ] Update corpus integrity tests so required fields and new metadata are
      present on every lesson.
- [ ] Update retrieval eval scenarios to cover the expanded source mix,
      including at least 60 fixed queries mapped to expected lesson filenames or
      canonical techniques.
- [ ] Add eval cases that require abstaining or reflecting instead of forcing an
      irrelevant technique.
- [ ] Re-run embedding upsert and verify unchanged chunks are not re-embedded.
- [ ] Compare retrieval with rerank on/off and at least two `top_k` values, such
      as `5` and `8`, then record the numbers in `evals/RESULTS.md`.
- [ ] Tighten the reply-quality judge so `grounded` requires applying one of the
      expected techniques or lessons, not merely naming any real technique.
- [ ] Document any source-category tradeoffs or excluded sources in this
      milestone or a short corpus note.

## Acceptance criteria

- `corpus/` contains at least 70 self-authored lesson chunks, and inspection
  finds no copied source passages.
- Every corpus entry includes `source`, `technique`, `lesson`, `use_when`,
  `avoid_when`, `example_application`, `situation_tags`, `query_phrases`, and
  `intervention_type`.
- The expanded corpus includes lessons from at least five distinct perspective
  families: habit automaticity/context, implementation planning, motivational
  interviewing or autonomy support, psychological flexibility or urge handling,
  and behavior diagnosis.
- Fixed-query retrieval evals include at least 60 scenarios across ordinary
  `log`s, coaching `reflection question`s, proactive nudge contexts, and
  abstention cases.
- Retrieval with rerank enabled improves or preserves hit-rate, recall, and MRR
  versus rerank disabled at the chosen production defaults. If it does not, the
  implementation records the failure and the next retrieval fix.
- At least 80% of fixed-query scenarios retrieve one expected lesson or
  technique in the top 3.
- At least 70% of fixed-query scenarios retrieve the best expected lesson or
  technique at rank 1 after reranking.
- The reply-quality judge penalizes replies that name a real but wrong
  technique, and the recorded results include this stricter criterion.
- At least one eval case proves Kaizen can avoid forcing a lesson when the
  retrieved lesson is irrelevant to the user's actual history.
- Re-running corpus embedding skips unchanged chunks and embeds only new or
  modified files.

## Verification

- `uv run pytest tests/rag tests/evals` passes, or a narrower equivalent slice
  is documented with the reason.
- `uv run python -m evals.retrieval` and
  `uv run python -m evals.retrieval --no-rerank` are run against the expanded
  corpus, and results are recorded in `evals/RESULTS.md`.
- If reply judge changes are made, `uv run python -m evals.runner` and
  `uv run python -m evals.runner --no-rerank` are run or explicitly deferred
  with the cost/runtime reason.
- `uv run ruff check .` is clean for Python changes.
- If schema changes are added, `uv run alembic upgrade head` succeeds.

## Sequencing notes

This milestone should happen before investing heavily in proactive nudge
phrasing. If the lesson corpus is too broad or sparse, the agent can correctly
detect drift but still choose shallow interventions.

The first implementation should prefer file-level corpus expansion and eval
updates over database schema work. Add structured storage only when markdown
metadata parsing becomes a bottleneck.

## Open questions

- The exact source list can change, but the final corpus must preserve a broad
  mix of perspectives rather than only adding more Atomic Habits/Tiny Habits
  variants.
- The project needs a practical naming convention for multiple lessons under
  the same technique, such as
  `implementation_intentions_late_work_gym.md` or a nested corpus directory.
- The target pass rates may need adjustment after the first expanded-corpus
  baseline, but any adjustment should be recorded with the observed failure
  modes rather than silently lowering the bar.

## Resume bullet unlocked

Expanded a self-authored behavioral-science lesson corpus from broad technique
notes into a 70+ chunk, eval-tested RAG knowledge base spanning habit
automaticity, planning, motivation, psychological flexibility, and behavior
diagnosis.
