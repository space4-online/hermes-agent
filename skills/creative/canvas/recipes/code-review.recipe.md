---
recipe: code-review
title: Code review canvas
authored_for: hermes-agent canvas skill
---

# Code review canvas

Render a single-file (or multi-hunk) diff alongside a reviewer comment thread.
Useful for:

- summarising a PR review in a single shareable PNG/SVG;
- attaching to release notes when a hot-fix needs explaining;
- onboarding contributors to a tricky changeset.

## Components used

- `FileReview` — header (path + summary) + diff body wrapper.
- `DiffGroup` — line-by-line diff renderer (used internally by `FileReview`).
- `ReviewThread` — vertical stack of `ReviewComment` blocks.
- `Tag` — risk / status chips at the top.

## Data model

```ts
type DiffLine = {
  kind?:  "ctx" | "add" | "del";
  oldNo?: number | string;     // left gutter ("" for inserted)
  newNo?: number | string;     // right gutter ("" for deleted)
  text:   string;              // raw line text, no trailing newline
};

type Comment = {
  author: string;
  body:   string;
  tone?:  "info" | "success" | "warning" | "danger";
};
```

## Recipe steps

1. **Heading band**: title + meta line (`N files · +A −B · risk: …`) + status
   tags row (`ready-to-merge`, `auth-touched`, etc.).
2. **Two-column body**: place `FileReview` on the left (≈ 60% width), the
   `ReviewThread` on the right (≈ 35% width). Use absolute `<g translate>` so
   the columns don't overlap.
3. **Order diff lines correctly**: keep `ctx` lines around `add`/`del` for
   anchoring; do not interleave hunks across files in one `FileReview`.
4. **Color discipline**: never hardcode add/del colors — `tokens.diff.*` already
   provides matched strip + foreground pairs.
5. **Comment count budget**: ≤ 4 comments per thread, ≤ 80 chars per line.
   Anything longer should link out to the PR.

## Variations

- **Multi-file**: stack multiple `FileReview` blocks vertically with a 16 px
  gap; cap each at ~12 lines so the page height stays manageable.
- **Heatmap risk**: replace the tags row with `RiskHeatmap` for projects that
  track per-area risk scores.
- **Decision banner**: top a banner above the body
  (`<Banner tone="warning" title="Requires DB migration before merge" />`).

## SVG Adaptation Notes

- Comment threads are static. Mark resolved threads visibly (`tone="success"`,
  trailing 〔resolved〕 in the body) instead of relying on a collapse hook.
- `wrapLines` inside `ReviewComment` uses a fixed-width estimate. Keep
  comment bodies plain text; line breaks (`\n`) are not preserved — use
  separate comments for clearly distinct points.
- The `DiffGroup` row gutter assumes line numbers fit in 56 px. For files
  past 100k lines, increase the `gutterW` constant in `code-view.mjs` or
  switch to short hashes.
- `Send to chat` buttons render as plain `Button`s — they are advisory only
  in offline output.
