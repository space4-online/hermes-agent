---
recipe: math-poster
title: Math & algorithm explainer (academic poster)
authored_for: hermes-agent canvas skill
---

# Math & algorithm explainer (academic poster)

A single-page, academic-conference-poster-styled explainer for one algorithm
or one mathematical theorem. Use this recipe when:

- onboarding readers to a single named algorithm (binary search, Dijkstra,
  KMP, FFT, RSA, …);
- presenting a derivation / lemma / closed form in study notes;
- printing a hallway poster for a university course or reading group.

## Visual identity (deliberate, fixed)

This recipe **does not** read from `useHostTheme()`. Academic posters carry a
self-contained visual identity that should remain stable across the host
editor's light/dark theme.

| role          | hex        | use for                                          |
|---------------|------------|--------------------------------------------------|
| ink (navy)    | `#1a2a4a`  | title band, section rules, body text             |
| accent        | `#7d2d3a`  | section labels, abstract strip, highlight cards  |
| highlight     | `#c89b3c`  | mustard band under title, list bullets, brand    |
| paper (cream) | `#fbf8f0`  | page background                                  |
| rule          | `#d8d2c2`  | hairline rules, table cell borders               |
| muted         | `#5b5e6b`  | captions, secondary footnotes                    |
| code bg       | `#f3eee0`  | pseudocode / formula card background             |

Typography is intentionally **serif everywhere** (`Georgia / Times New Roman`)
except for code/math, which uses a `SFMono-Regular` mono fallback. This is what
makes the page read as "academic" rather than "product UI".

## Layout grid (W = 1100, H = 1200)

```
0────────────────────────────────────────── 1100
│ Title band (navy + mustard underline)        │ 0 – 110
│ Abstract strip (white, accent left rule)     │ 130 – 194
│                                              │
│ ┌── Problem ────────┐  ┌── Algorithm ─────┐  │ 220 – 720
│ │ prose            │  │ pseudocode block │  │
│ ├── Invariant ─────┤  ├── Recurrence ────┤  │
│ │ prose + formula  │  │ formulas + prose │  │
│ ├── Figure ────────┤  └──────────────────┘  │
│ │ shrinking window │                         │
│ └──────────────────┘                         │
│                                              │
│ Empirical step counts (full-width table)     │ 790 – 950
│                       Key takeaways (right)  │ 980 – 1130
│ References footer (navy band)                │ 1140 – 1190
```

Two columns at 490 px each, gutter 40 px, outer margin 40 px.

## Anatomy

| Block            | What it is                                                        |
|------------------|--------------------------------------------------------------------|
| `TitleBand`      | Navy hero band + mustard underline + serif title + brand strap.    |
| `Abstract`       | One-paragraph summary in a white card with a left accent rule.     |
| `Section`        | Hairline rule + uppercase wide-letter-spaced section label.        |
| `Formula`        | White card with a centered italic-serif equation.                  |
| `CodeBlock`      | Cream-tinted block with monospace pseudocode lines.                |
| `ShrinkingWindow`| Visual proof that each step halves the candidate window.           |
| `ComparisonTable`| Striped numeric table with serif first/last column, mono middle.   |
| `Takeaways`      | White card with accent border + mustard bullets.                   |
| `Footer`         | Navy band with mustard `REFERENCES` label and 3 inline citations.  |

## Recipe steps

1. **Replace the `POSTER` content block** at the top of the template with your
   own data: `title`, `subtitle`, `abstract[]`, `problem[]`, `pseudocode[]`,
   `recurrence`, `closedForm`, `derivation[]`, `table.{headers,rows}`,
   `takeaways[]`, `references[]`.
2. **Keep the column structure**: left column is conceptual (problem ➜
   invariant ➜ figure), right column is mechanical (algorithm ➜ closed form).
3. **Math formatting**: write equations in plain Unicode (`Θ`, `≤`, `⌊⌋`,
   `⟹`, subscripts via `₀..₉`). Reserve LaTeX-style markup only when the
   poster is converted downstream.
4. **Pseudocode style**: `←` for assignment, `:` after the predicate, no
   trailing semicolons. Indent with 4 spaces.
5. **Pick a Figure that proves the bound visually**. Default is
   `ShrinkingWindow` for halving algorithms; swap for a recursion tree, a
   lattice, or a state machine when the algorithm shape changes.
6. **Cap takeaways at 4 items** of ≤ 60 characters each so the right card
   stays readable next to the table.
7. **Cap references at 3 items**; the footer renders inline at fixed
   `40 + i*340` px offsets and will overflow otherwise.

## Variations

- **Theorem poster**: rename `Algorithm` ➜ `Statement`, replace pseudocode
  with the theorem statement, replace the table with a worked-example block.
- **Comparative poster**: drop `ShrinkingWindow`, use the `Figure` slot for a
  side-by-side benchmark plot built from the existing primitives in
  [`scripts/sdk/charts.mjs`](file:///Users/paladnix/project/codeshark/hermes-agent/skills/creative/canvas/scripts/sdk/charts.mjs).
- **Bilingual poster**: render twice with translated `POSTER` blocks; concat
  via an external SVG composer.

## SVG Adaptation Notes

- `useHostTheme()` is **deliberately not used**. Hard-coded hex values are
  acceptable here because the visual identity is the point of this template.
- All section labels use `letterSpacing="0.2em"` — preserved by the runtime's
  camelCase conversion (becomes `letter-spacing` in the SVG output).
- Formulas are plain `<text>` runs; no MathML, no KaTeX. For multi-line
  derivations, stack multiple `Formula` cards inside a single `Section`.
- `Footer` lays its 3 references at `x = 40 + i*340`. Add a fourth only if
  you also widen the page beyond 1100 or shrink the per-citation slot.
- The page is fixed at `W=1100, H=1200`. Always pass `--width 1100 --height
  1200` when rendering, otherwise the auto-height heuristic in
  [`render.mjs`](file:///Users/paladnix/project/codeshark/hermes-agent/skills/creative/canvas/scripts/render.mjs)
  may overshoot or clip.
