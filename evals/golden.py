"""Golden eval set for Kaizen retrieval evals.

Each scenario maps a natural-language daily log to the corpus techniques
(filename stems, no .md) that a good response should be grounded in, plus
a one-line note for the future LLM-as-judge step.

Seeded from:
- tests/extract/test_extractor.py EXAMPLES (m2 hand-written logs)
- tests/rag/test_rag.py query + technique names (m3)
- All 15 corpus filenames verified against corpus/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Scenario:
    log: str
    expected_techniques: list[str] = field(default_factory=list)
    ideal_notes: str = ""

    def __post_init__(self) -> None:
        # frozen dataclass requires object.__setattr__ for validation side-effects
        object.__setattr__(self, "expected_techniques", list(self.expected_techniques))


@dataclass(frozen=True)
class LessonGroundingScenario:
    mode: Literal["descriptive_reflection", "coaching_reflection", "abstain", "proactive"]
    prompt: str
    history: str
    expected_techniques: list[str] = field(default_factory=list)
    ideal_notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected_techniques", list(self.expected_techniques))


# ---------------------------------------------------------------------------
# Seeded from m2 extraction examples
# ---------------------------------------------------------------------------

GOLDEN_SET: list[Scenario] = [
    # --- from EXAMPLES in test_extractor.py ---
    Scenario(
        log="Went for a 30 min run this morning. Feeling great!",
        expected_techniques=["progress_tracking", "identity_based_habits"],
        ideal_notes="Affirm the streak, reinforce runner identity, suggest logging it.",
    ),
    Scenario(
        log="Skipped meditation again today. Work was too stressful.",
        expected_techniques=["relapse_recovery", "if_then_planning"],
        ideal_notes="Normalise the lapse, offer an if-then trigger to restart tomorrow.",
    ),
    Scenario(
        log="Did half my workout — only 20 mins instead of 45. Tired from yesterday.",
        expected_techniques=["self_compassion_after_failure", "two_minute_rule"],
        ideal_notes="Validate partial effort, reframe as a win, suggest a shorter anchor.",
    ),
    Scenario(
        log="Journaled for 10 minutes before bed. Also drank 8 glasses of water today.",
        expected_techniques=["habit_stacking", "progress_tracking"],
        ideal_notes="Celebrate multi-habit day, suggest stacking them as a routine.",
    ),
    Scenario(
        log="Couldn't sleep well. Skipped both morning run and reading.",
        expected_techniques=["relapse_recovery", "self_compassion_after_failure"],
        ideal_notes="Acknowledge root cause (sleep), encourage recovery without guilt.",
    ),
    Scenario(
        log="Had a salad for lunch instead of fast food. Small win!",
        expected_techniques=["identity_based_habits", "environment_design"],
        ideal_notes="Reinforce identity ('I eat well'), suggest friction-reduction tactics.",
    ),
    # --- from test_rag.py RAG query ---
    Scenario(
        log="Skipped gym again, just had no motivation today.",
        expected_techniques=["motivation_wave", "implementation_intentions"],
        ideal_notes="Explain motivation wave, offer a concrete if-then plan for tomorrow.",
    ),
    # --- additional varied scenarios ---
    Scenario(
        log="I've been hitting my 10k steps goal every day for two weeks straight!",
        expected_techniques=["progress_tracking", "identity_based_habits"],
        ideal_notes="Celebrate streak, suggest scaling the goal or adding complexity.",
    ),
    Scenario(
        log="Tried to quit sugar but had cake at the office birthday party. Feel terrible.",
        expected_techniques=["self_compassion_after_failure", "relapse_recovery"],
        ideal_notes="Reframe social eating, prevent all-or-nothing spiral.",
    ),
    Scenario(
        log="Put my running shoes next to the bed last night — actually went this morning!",
        expected_techniques=["environment_design", "friction_reduction"],
        ideal_notes="Reinforce the cue placement strategy, suggest extending it.",
    ),
    Scenario(
        log="I always want to meditate but by evening I'm too tired and skip it.",
        expected_techniques=["if_then_planning", "implementation_intentions"],
        ideal_notes="Help user pin a specific time/trigger for the habit.",
    ),
    Scenario(
        log="Told my friend I'd run a 5k with her in March. Feeling accountable now.",
        expected_techniques=["commitment_devices"],
        ideal_notes="Validate the commitment device, suggest a public tracking add-on.",
    ),
    Scenario(
        log="I stack my vitamins next to the coffee machine so I never forget.",
        expected_techniques=["habit_stacking", "environment_design"],
        ideal_notes="Confirm the technique, suggest another habit to attach nearby.",
    ),
    Scenario(
        log="Read for 30 minutes instead of scrolling at night — third time this week.",
        expected_techniques=["friction_reduction", "progress_tracking"],
        ideal_notes="Acknowledge the friction swap, reinforce the streak.",
    ),
    Scenario(
        log="Keep telling myself I'll start the diet on Monday, but Monday never comes.",
        expected_techniques=["implementation_intentions", "commitment_devices"],
        ideal_notes="Surface the start-on-Monday trap, offer a concrete trigger plan.",
    ),
    Scenario(
        log="Meditated for 2 minutes just to say I did it. Felt silly but I did it.",
        expected_techniques=["two_minute_rule", "self_compassion_after_failure"],
        ideal_notes="Validate the two-minute anchor, encourage building from there.",
    ),
    Scenario(
        log="I always crave snacks when I'm bored at 3pm. Ate chips again.",
        expected_techniques=["urge_surfing", "reward_substitution"],
        ideal_notes="Teach urge-surfing the 3pm craving, suggest a substitute reward.",
    ),
    Scenario(
        log="Gym was packed so I left without working out. Really frustrated.",
        expected_techniques=["if_then_planning", "friction_reduction"],
        ideal_notes="Build a contingency if-then for busy gym days.",
    ),
    Scenario(
        log="Woke up at 5:30 and meditated. Feeling like a completely different person.",
        expected_techniques=["identity_based_habits", "motivation_wave"],
        ideal_notes="Reinforce identity shift, anchor the feeling to the routine.",
    ),
    Scenario(
        log="Had a rough week — missed three workouts and ate terribly. Starting over.",
        expected_techniques=["relapse_recovery", "self_compassion_after_failure"],
        ideal_notes="Offer the 'never miss twice' rule, compassionate restart framing.",
    ),
    Scenario(
        log="I listen to a podcast I love only during runs. Makes me want to run more.",
        expected_techniques=["temptation_bundling"],
        ideal_notes="Name temptation bundling explicitly, suggest extending it.",
    ),
    Scenario(
        log="Deleted TikTok from my phone. Read 20 pages tonight without thinking.",
        expected_techniques=["friction_reduction", "environment_design"],
        ideal_notes="Praise the removal of the competing stimulus, suggest next step.",
    ),
    Scenario(
        log="Logged all my meals today but went 400 calories over. At least I tracked.",
        expected_techniques=["progress_tracking", "self_compassion_after_failure"],
        ideal_notes="Celebrate tracking consistency independent of outcome.",
    ),
    Scenario(
        log="Signed up for a month-long step challenge at work with a cash pool.",
        expected_techniques=["commitment_devices", "progress_tracking"],
        ideal_notes="Validate the social + financial commitment device.",
    ),
    Scenario(
        log="Tried urge surfing when I wanted to check Instagram — it actually worked.",
        expected_techniques=["urge_surfing"],
        ideal_notes="Reinforce the technique success, suggest broader application.",
    ),
]


LESSON_GROUNDING_SET: list[LessonGroundingScenario] = [
    LessonGroundingScenario(
        mode="descriptive_reflection",
        prompt="when do I usually skip gym?",
        history="Gym misses cluster after late work nights.",
        expected_techniques=[],
        ideal_notes=(
            "Answer from logs and memory only. Forcing a lesson or technique is penalized "
            "because the user asked for description, not advice."
        ),
    ),
    LessonGroundingScenario(
        mode="coaching_reflection",
        prompt="what should I change tomorrow?",
        history="The user missed gym twice after late work and then doomscrolled.",
        expected_techniques=["implementation_intentions", "if_then_planning"],
        ideal_notes=(
            "Use recent history first, then apply one matching lesson by naming the "
            "technique and tying it to the late-work pattern."
        ),
    ),
    LessonGroundingScenario(
        mode="abstain",
        prompt="what should I change about my reading habit?",
        history=(
            "The user completed reading daily this week; retrieved snack-craving lessons "
            "do not fit."
        ),
        expected_techniques=[],
        ideal_notes=(
            "A good answer does not force an irrelevant lesson. It should answer from "
            "history only or say no lesson is needed right now."
        ),
    ),
    LessonGroundingScenario(
        mode="proactive",
        prompt="scheduled tick: decide whether to nudge",
        history="Habit state says gym is missing; memory says late work caused two recent misses.",
        expected_techniques=["implementation_intentions", "if_then_planning"],
        ideal_notes=(
            "A useful nudge uses a lesson query containing the habit and recent pattern, "
            "then applies a matching planning technique or stays silent."
        ),
    ),
]
