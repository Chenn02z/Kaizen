# Lesson Format

Lessons live in `docs/learning/kaizen/lessons/` and default to Markdown: `0001-slug.md`, `0002-slug.md`, etc. Use HTML only when the exercise needs browser-native interaction or richer visual explanation.

## Template

```md
# Lesson {NNNN}: {Title}

## Why this matters for Kaizen
{1-3 sentences tying the concept to the current milestone, feature, or architectural decision.}

## Starting point in the repo
- `{path/to/file.ext}` — {what to inspect here}
- `{path/to/test.ext}` — {what this proves or checks}

## Core idea
{A short explanation with only the knowledge needed for this lesson. Cite local or external sources where useful.}

## Worked example
{Walk through one concrete example from this repo.}

## Your exercise
{One small task, retrieval prompt, or inspection exercise. Keep it short.}

## Check for understanding
- {Question 1}
- {Question 2}

## Portfolio angle
{How this concept shows up as an interview-worthy artifact, tradeoff, or story in the repo.}

## Next links
- [Related lesson](./0002-next-lesson.md)
- [Reference note](../reference/example.md)

## Primary sources
- `{local/path/or/url}` — {why this is the primary source}
```

## Rules

- **One lesson, one win.** Teach one tightly-scoped concept or skill, not a whole subsystem.
- **Repo-grounded by default.** A lesson should point to actual files, tests, or milestone docs whenever possible.
- **Exercise required.** Every lesson needs a small retrieval or application task.
- **Portfolio angle required.** Explicitly connect the learning to something the user can later explain in an interview.
- **Prefer Markdown.** HTML is the exception, not the default.
