# HTML Report Format

Render the architecture review as a single self-contained HTML file in the OS
temp directory. Tailwind and Mermaid both come from CDNs. Mermaid handles
graph-shaped diagrams reliably; hand-built divs and inline SVG handle editorial
visuals such as mass diagrams and cross-sections. Mix the two.

## Scaffold

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Kaizen architecture review - {{date}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
    </script>
    <style>
      /* small custom layer for things Tailwind doesn't cover cleanly:
         dashed seam lines, hand-drawn-feeling arrow heads, etc. */
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header>...</header>
      <section id="candidates" class="space-y-10">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

## Header

Use "Kaizen architecture review", the date, and a compact legend:

- solid box = module
- dashed line = seam
- red arrow = leakage
- thick dark box = deep module
- amber note = doc or milestone tension

Do not write a generic introduction. Go straight into the candidates.

## Candidate card

The diagrams carry the weight. Prose is sparse, plain, and uses the architecture
terms from `SKILL.md` plus Kaizen domain terms from `docs/CONTEXT.md`.

Each candidate is one `<article>`:

- **Title**: short, names the deepening, such as "Deepen proactive intervention recording".
- **Badge row**: recommendation strength (`Strong` = emerald, `Worth exploring` = amber, `Speculative` = slate), plus the area (`backend`, `agent`, `RAG`, `evals`, `frontend`, `docs`).
- **Files**: monospaced list, `font-mono text-sm`.
- **Before / After diagram**: the centerpiece. Two columns, side by side.
- **Problem**: one sentence naming the friction.
- **Solution**: one sentence naming what changes.
- **Wins**: bullets, six words or fewer.
- **Milestone/doc callout**: one line in an amber-tinted box when relevant.

No paragraphs of explanation. If the diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns

Pick the pattern that fits the candidate. Mix them. Do not make every diagram
look the same.

### Mermaid graph (the workhorse for dependencies / call flow)

Use a Mermaid `flowchart` or `graph` when the point is call flow, dependency
shape, or leakage. Wrap it in a Tailwind-styled card. Style with `classDef` to
color leakage edges red and the deep module dark. Sequence diagrams work well
for "before: 6 hops; after: 1 interface".

```html
<div class="rounded-lg border border-slate-200 bg-white p-4">
  <pre class="mermaid">
    flowchart LR
      A[Webhook] --> B[Extractor]
      B --> C[Habit Planner]
      C -.leak.-> D[Memory Payload]
      classDef leak stroke:#dc2626,stroke-width:2px;
      class C,D leak
  </pre>
</div>
```

### Hand-built boxes-and-arrows (when Mermaid's layout fights you)

Modules as `<div>`s with borders and labels. Arrows as inline SVG `<line>` or
`<path>` elements positioned absolutely over a relative container. Use this when
the after diagram should show one thick-bordered deep module with faded
internals.

### Cross-section (good for layered shallowness)

Stack horizontal bands (`h-12 border-l-4`) to show layers a call passes through. Before: 6 thin layers each doing nothing. After: 1 thick band labelled with the consolidated responsibility.

### Mass diagram (good for "interface as wide as implementation")

Two rectangles per module: one for interface surface area, one for implementation. Before: interface rectangle is nearly as tall as the implementation rectangle (shallow). After: interface rectangle is short, implementation rectangle is tall (deep).

### Call-graph collapse

Before: a tree of function calls rendered as nested boxes. After: the same tree collapsed into one box, with the now-internal calls shown faded inside it.

## Style guidance

- Lean editorial, not corporate-dashboard. Generous whitespace. Serif optional for headings (`font-serif` works well with stone/slate).
- Colour sparingly: one accent (emerald or indigo) plus red for leakage and amber for warnings.
- Keep diagrams ~320px tall so before/after sits comfortably side by side without scrolling.
- Use `text-xs uppercase tracking-wider` for module labels inside diagrams.
- The only scripts are the Tailwind CDN and the Mermaid ESM import. The report is otherwise static.

## Top recommendation section

One larger card. Candidate name, one sentence on why, anchor link to its card. That's it.

## Tone

Plain English, concise, and grounded in Kaizen's actual product behavior.

**Use exactly:** module, interface, implementation, depth, deep, shallow, seam,
adapter, leverage, locality.

**Use Kaizen terms:** log, habit, technique, grounded reply, memory, nudge,
intervention, quiet hours, check-in.

**Avoid substitutes:** component, service, unit for module; API or signature for
interface; boundary for seam; layer or wrapper for module when module is meant.

**Phrasings that fit the style:**

- "Intervention recording is shallow: callers assemble too much state."
- "Memory payload shape leaks across the seam."
- "Deepen: one interface, one place to test."
- "Two adapters justify the seam: Telegram in production, in-memory in tests."

**Wins bullets** name the gain in glossary terms: "locality: one module owns
rules", "leverage: one interface, many tests", "interface shrinks; implementation
absorbs call choreography". Do not write "cleaner code" unless the sentence says
what changed structurally.

No hedging and no throat-clearing. If a sentence could be a bullet, make it a
bullet. If a bullet could be cut, cut it.
