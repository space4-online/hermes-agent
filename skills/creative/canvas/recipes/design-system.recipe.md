---
recipe: design-system
title: Design system cheatsheet
authored_for: hermes-agent canvas skill
---

# Design system cheatsheet

A one-page reference that documents the visual vocabulary of a project: status
tones, primary buttons, cards, and KPI tiles. Use this recipe when:

- a project has just been wired up and needs an internal "house style" page;
- you need to demo the canvas SDK's primitives in one shot;
- you want to compare light vs dark themes side-by-side.

## Components used

- `DocsSection` — titled rule-line section header with consistent padding.
- `Banner` — top-of-page advisory.
- `Tag` / `Pill` — token swatches by tone.
- `Button` — primary / secondary / ghost / danger variants.
- `MetricsGrid` — N-column stat tiles.
- `Card` + `Callout` + `Stat` — example composition row.

## Recipe steps

1. **Header**: `H1` with the project name, `Text` subtitle showing the active
   theme (`mode` from `useHostTheme()`).
2. **Banner**: a 1020 px wide `tone="info"` banner reminding readers to read
   colors from `tokens.*`, not literal hex.
3. **Section per concept**: wrap each topic in a `DocsSection` so the
   uppercase rule-line label gives a consistent visual rhythm.
4. **Tags row, then buttons row**: keep both at fixed `x` offsets; avoid
   relying on flex layout.
5. **Composition row**: end with one `Card` + `Callout` + `Stat` to show how
   primitives stack up to richer surfaces.

## Variations

- **Light/dark side-by-side**: render twice (once per theme) and stitch with
  an external SVG composer, or duplicate the body inside one canvas with two
  translated `<g>` blocks calling `applyTheme()` per render.
- **Token grid**: replace the tones row with a 6×N grid where each cell shows
  a token name + its hex. Use `Code` for the hex value.
- **Component matrix**: tabulate each primitive × each tone (e.g. `Button`
  variants × danger/warning/info) using `Table`.

## SVG Adaptation Notes

- The page has **no scroll**. Aim for ≤ 800 px in height; for taller content
  switch to a multi-page approach (one canvas per concept).
- `applyTheme()` is **module-level** — switching mid-render affects all later
  elements. Render two separate canvases instead of trying to mix themes in
  one tree.
- `MetricsGrid` deltas accept arbitrary strings (`"+12%"`, `"-0.3pp"`). The
  arrow direction is derived from `delta.direction`, not the sign of the
  number.
- All `Card` accents render as a 4 px-wide left strip; pass any token color
  (`tokens.primary.color`, `tokens.status.danger`) for emphasis.
