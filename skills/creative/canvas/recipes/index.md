# Canvas recipes

Each recipe is a copy-paste-friendly authoring guide for one canvas archetype.
The matching `templates/<name>.canvas.tsx` next to this folder is a runnable
starting point; render it with:

```bash
node scripts/render.mjs templates/<name>.canvas.tsx --width 1080
```

## Available recipes

Each row links a recipe to its template **and** to a rendered preview image.
When the user is unsure which one to pick, show the preview images inline
(see `SKILL.md` → *Template selection protocol*).

| Recipe                                          | Template                                            | Preview                                                | Use when |
|-------------------------------------------------|-----------------------------------------------------|--------------------------------------------------------|----------|
| [code-review](./code-review.recipe.md)          | `templates/code-review.canvas.tsx`                  | `examples/code-review.svg.png`                         | summarising a PR / single-file diff with reviewer threads |
| [design-system](./design-system.recipe.md)      | `templates/design-system.canvas.tsx`                | `examples/design-system.svg.png` (light) / `examples/design-system-dark.svg.png` (dark) | producing a tokens / primitives cheat sheet for a project |
| [math-figure](./math-figure.recipe.md)          | `templates/math-figure.canvas.tsx`                  | `examples/math-figure.svg.png`                         | embedding a single paper-grade figure (architecture, state machine, tree) — monochrome |
| math-figure-transformer (variant of math-figure) | `templates/math-figure-transformer.canvas.tsx`     | `examples/math-figure-transformer.svg.png`             | same scale as math-figure, but with a categorical color palette (Transformer-style) |
| [math-poster](./math-poster.recipe.md)          | `templates/math-poster.canvas.tsx`                  | `examples/math-poster.svg.png`                         | explaining one algorithm / theorem in academic-poster style |
| [sequence-diagram](./sequence-diagram.recipe.md)| `templates/sequence-diagram.canvas.tsx`             | `examples/sequence-diagram.svg.png`                    | rendering interaction flows between services / modules |

## Authoring rules of thumb

1. **Always wrap the document in a single `<g>`** so absolute coordinates inside
   the component compose cleanly when nested.
2. **Read colors from `useHostTheme().tokens`**, never hardcode hex.
3. **Layout is explicit**: place children with `<g transform="translate(x, y)">`.
   The runtime does not implement flex / grid auto-sizing.
4. **Pure render** — `useState` / `useEffect` are no-ops in this runtime; do
   not depend on event handlers firing. The output is a static SVG.
5. **Pass-through SVG** — primitives like `path`, `defs`, `marker`, `linearGradient`
   are honoured verbatim. Use them for diagram glue (arrows, gradients, masks).
