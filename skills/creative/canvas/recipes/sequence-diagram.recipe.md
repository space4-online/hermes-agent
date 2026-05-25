---
recipe: sequence-diagram
title: Sequence diagram
authored_for: hermes-agent canvas skill
---

# Sequence diagram

A sequence diagram shows messages exchanged between **lanes** (actors / services)
along a vertical time axis. Use this recipe when:

- explaining a request-response flow across services;
- documenting a saga / orchestration with branching outcomes;
- onboarding teammates to a new module's interaction surface.

## Anatomy

| Layer        | What it is                                                      |
|--------------|------------------------------------------------------------------|
| Lane headers | Boxed labels at the top, one per actor.                          |
| Lifelines    | Dashed vertical lines descending from each lane header.          |
| Activations  | Narrow vertical bars on a lifeline showing "this actor is busy". |
| Messages     | Arrows between lifelines, labelled at the midpoint.              |
| Legend       | Small tag row at the bottom describing arrow kinds.              |

## Data model

Keep the data above the JSX. The template uses three flat arrays:

```ts
type Lane        = { id: string; label: string; x: number };
type Activation  = { lane: string; y1: number; y2: number };
type Message     = { from: string; to: string; y: number; label: string;
                     kind?: "sync" | "async" | "return" };
```

Each `y` is an absolute pixel inside the canvas. Resist the urge to compute
times — explicit y values keep the SVG diff-friendly.

## Recipe steps

1. **Pick lane x-coordinates** at fixed columns (e.g. 120 / 360 / 600 / 840).
   Use the same step for every lane to keep arrows readable.
2. **Reserve the top band** (y=0..70) for the title + lane headers.
3. **Walk down in y-increments of 30–40 px** for each message; group activations
   so they wrap the relevant span.
4. **Define markers in `<defs>`** once for `arrow-sync` and `arrow-return`; refer
   to them via `markerEnd="url(#arrow-sync)"`.
5. **Render in fixed order**: lifelines first, then activations, then messages,
   then the legend — later layers paint on top.

## Variations

- **Async messages**: omit the `markerEnd` solid arrowhead and use
  `strokeDasharray="4 3"` plus a half-arrow marker.
- **Self-call**: draw a small loop with two `path` commands ending back on the
  same lifeline; place the label to the right.
- **Notes**: drop a `<Callout tone="neutral" width={...} />` between two
  messages to annotate decisions.

## SVG Adaptation Notes

The original Qoder recipe expected a live host that provided themes, layout
and interactivity. In this offline build:

- `useHostTheme()` returns a snapshot picked by `--theme light|dark`.
- `Stack` / `Row` exist but **do not flex**; for diagrams, prefer manual
  `<g transform="translate(x, y)">` placement so message anchors stay stable.
- `<marker>` elements must live inside a `<defs>` block of the rendered tree.
  The walker emits them verbatim, but `markerWidth` / `markerHeight` / `refX`
  must stay camelCase (the runtime preserves them via `KEEP_CAMEL`).
- Avoid `useState` for collapse/expand — the SVG is static; render the
  intended state directly.
