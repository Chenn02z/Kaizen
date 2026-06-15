# RESOURCES.md Format

`RESOURCES.md` is the curated set of trusted sources for this topic. Knowledge for explainers should be drawn from here, not from parametric guesses. In a software project, local project artifacts are often the first source to consult. Wisdom comes from the communities listed here.

## Structure

```md
# {Topic} Resources

## Local project sources

- `docs/PRODUCT.md`
  Product intent and success criteria. Use for: why this system exists and what "good" means.
- `docs/milestones/03-rag.md`
  Acceptance criteria for a specific milestone. Use for: the exact capability the current lesson should support.
- `app/rag/retrieve.py`
  Concrete implementation. Use for: the worked example that turns the concept into code.
- `tests/` or `evals/`
  Evidence and guardrails. Use for: how correctness or quality is measured.

## External knowledge

- [Official docs or paper](https://example.com)
  Trusted external source. Use for: definitions, APIs, or research claims not already captured in the repo.

## Wisdom (Communities)

- [High-signal community](https://example.com)
  Use for: practitioner tradeoffs, debugging stories, and real-world feedback loops.
```

## Rules

- **Local first.** Start with repo docs, code, tests, and evals when they answer the question. External resources should deepen or verify, not replace, project context.
- **High-trust only.** Prefer primary sources, recognised experts, peer-reviewed work, and communities with strong moderation. If a resource is marketing dressed as education, leave it out.
- **Prefer official docs for tools.** For frameworks, SDKs, and APIs, the default external source should be the official documentation or primary paper.
- **Annotate every entry.** A bare link is useless in three months. Add one line: what it covers and when to reach for it.
- **Group by Local project sources / External knowledge / Wisdom.** This mirrors how teaching should proceed in this repo.
- **Surface gaps explicitly.** If no good resource exists for an area the mission needs, write a `## Gaps` section listing what is missing. This drives future search.
- **Prune ruthlessly.** A resource that turned out to be wrong, shallow, or off-mission should be removed, not buried. Better five sharp sources than thirty mediocre ones.
- **Record community preferences.** If the user has opted out of joining communities, note it here so future sessions don't keep proposing them.
