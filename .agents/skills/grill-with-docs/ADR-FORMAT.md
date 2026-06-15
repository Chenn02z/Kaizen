# ADR Format

ADRs live in `docs/adr/` and use sequential numbering: `0001-slug.md`,
`0002-slug.md`, and so on.

Create `docs/adr/` lazily, only when the first ADR is worth writing.

## Template

```md
# Short title of the decision

1-3 sentences covering the context, the decision, and why it was made.
```

Keep the body short. The value of an ADR is that a future reader can see that a
decision was made and why.

## Optional sections

Add these only when they carry useful signal:

- `Status` frontmatter: `proposed`, `accepted`, `deprecated`, or `superseded by
  ADR-NNNN`
- `Considered options`: only when rejected alternatives are worth preserving
- `Consequences`: only when downstream effects are not obvious

## Numbering

Scan `docs/adr/` for the highest existing number and increment by one.

## When to offer an ADR

Offer an ADR only when all three are true:

1. Hard to reverse
2. Surprising without context
3. A real trade-off with genuine alternatives

If a decision is easy to reverse, skip it. If it is obvious, skip it. If there
was no meaningful alternative, record it in prose elsewhere rather than forcing
an ADR.

## What qualifies

Good ADR candidates in Kaizen are decisions like:

- the overall architecture shape
- boundaries between agent, RAG, memory, and backend code
- model gateway choices or other lock-in-heavy integrations
- explicit scope decisions, such as single-user-only behavior
- deliberate deviations from the obvious path
- constraints that are not visible in the code
- non-obvious rejected alternatives

## Notes

- Prefer a short, readable paragraph over a template full of empty sections.
- Use the repo's terminology from `AGENTS.md`, `docs/PRODUCT.md`, and
  `docs/CONTEXT.md` when naming the decision.
