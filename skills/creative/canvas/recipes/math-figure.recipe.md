# Recipe — Math / Algorithm Figure (paper-figure scale)

A single illustration at the granularity of one paper figure: an architecture
diagram, a state machine, a data-structure layout, or a small geometric
construction. The whole canvas is one figure block — title-and-description
caption sits at the bottom; the visual occupies the top 70 %.

This is the small sibling of `math-poster`. Use this when you only need
**one** picture; reach for `math-poster` when you want the surrounding
narrative (abstract, invariants, recurrence, takeaways).

> Default subject in the template: a multilayer perceptron architecture
> diagram. Substitute the body of `<NetworkGraph />` to repurpose.

## When to use this recipe

- Embedding a figure in a paper, technical note, or lecture slide.
- Replacing a hand-drawn schematic with a clean vector version.
- Documenting an architecture, an automaton, or a data-structure shape
  with one diagram and a short caption.

Pick `math-poster` instead when you need a multi-section, full-page
academic-poster layout.

## Visual identity

| Token              | Value      | Used for                                  |
| ------------------ | ---------- | ----------------------------------------- |
| `PAL.ink`          | `#1a1a1a`  | Strokes, primary text                     |
| `PAL.bg`           | `#ffffff`  | Page (print-friendly)                     |
| `PAL.nodeFill`     | `#ffffff`  | Default node fill                         |
| `PAL.nodeStroke`   | `#1a1a1a`  | Default node stroke                       |
| `PAL.edge`         | `#cfd2d6`  | Connection lines (intentionally thin)     |
| `PAL.accent`       | `#1a4f9c`  | Highlight stroke (e.g. output / focus)    |
| `PAL.accentSoft`   | `#e9eef9`  | Highlight fill                            |
| `PAL.caption`      | `#333333`  | Caption body text                         |
| `PAL.rule`         | `#bfc3c9`  | Rule line above the caption               |

Typography is mostly serif (`Georgia` family) for caption and dimension
annotations, sans-serif (`Helvetica Neue`) for short labels under nodes.
This mirrors typical paper figures where caption text is set in the body
font and graph labels are set in a clean sans face.

## Layout grid

```
0 ─────────────────────────────────── 720 (W)
│                                            │
│   W₁          W₂          W₃               │  100  ← weight-matrix labels
│                                            │
│   ●  ─────  ●  ─────  ●  ─────  ●          │  band 100..320
│   ●         ●         ●         ●          │
│   ●         ●         ●         ●          │
│   ●         ●         ●                    │
│             ●         ●                    │
│             ●         ●                    │
│  input    hidden 1  hidden 2   output      │  ~360 (layer labels)
│  x∈ℝ⁴     ReLU      ReLU       softmax     │
│  d=4      d=6       d=6        d=3         │
│                                            │
│ ────────────────────────────────────────── │  ~390 (rule)
│ Figure 1. Multilayer perceptron …          │  caption block
│ Fully-connected feed-forward …             │
│                                            │
0 ─────────────────────────────────── 460 (H)
```

Horizontal layer spacing is computed from `(L − 1)` gaps so adding /
removing layers redistributes them automatically.

## Anatomy

### Page background
Plain white rectangle filling `W × H`. Keep it white — paper figures must
be printable and must overlay text columns without color clash.

### `<NetworkGraph />`
The interchangeable body. For an MLP it draws:

1. **Weight-matrix labels** above the inter-layer gaps (`W₁`, `W₂`, `W₃`).
2. **All edges first**, with `strokeWidth={0.7}` and a near-invisible gray.
   This ensures node strokes win the visual hierarchy when they overlap.
3. **Nodes**, drawn after edges. Accented layers use the soft-blue fill
   plus blue stroke; default layers are white-on-black-stroke circles.
4. **Layer labels** below the band: name (sans, bold), formula (serif
   italic), dimension count (sans, light).

### `<Caption />`
A horizontal rule, then `Figure N.` (bold serif) and the title (italic
serif) on the same baseline, followed by 2–3 description lines (serif
roman). Keep each line ≤ 110 chars so they fit the column at 11 pt.

## Recipe steps

1. **Decide the figure subject.** Architecture? State machine? Tree?
   Geometric proof? The Caption template stays; the body changes.
2. **Edit `FIGURE`** at the top of the template — it is the only place
   that should change for an MLP variant. Adjust `layers[]`, `title`,
   `caption[]`, and the figure number.
3. **For non-MLP subjects, replace `<NetworkGraph />`** with your own
   `<g>…</g>`. Reuse the `PAL` and `SERIF`/`SANS` constants so the figure
   keeps the same paper look.
4. **Use Unicode math glyphs**: ℝ, ⁴, ₁, Θ, ≤, ⌊⌋, ∈, ⟹, ŷ. Do not import
   LaTeX/MathML — the SDK has no math typesetter, but Unicode covers most
   inline math seen in paper figures.
5. **Pick exactly one accent layer / element.** Paper figures have one
   focal point (the output, the start state, the proof step under
   discussion). Multiple accents flatten the hierarchy.
6. **Keep edges thin and gray.** Strong edges + strong nodes = visual
   noise. The convention in ML papers is `~0.5–1 px` light gray edges.
7. **Render at the native size**:

   ```bash
   node scripts/render.mjs templates/math-figure.canvas.tsx \
     --width 720 --height 460 \
     -o examples/math-figure.svg
   ```

## Variations

- **State machine.** Replace nodes with circled labels, edges become
  arrowheaded paths with transition labels. Keep the soft-blue accent for
  the start state and a doubled circle for accept states.
- **Binary tree / heap.** Compute positions from in-order index; reuse
  `<Caption />` unchanged. Add depth-line annotations on the right edge.
- **Convergence plot.** Drop the caption block to `H − 80`, sketch axes
  with two `<line>`s, plot a few `<polyline>` curves with `PAL.accent`
  for the proposed method and `PAL.muted` for baselines.
- **Accent palette swap.** If your paper uses a different brand color,
  change `PAL.accent` and `PAL.accentSoft` together — the rest of the
  diagram is intentionally desaturated and stays neutral.
- **Categorical palette (multi-color architecture).** When the figure
  needs to distinguish 4–9 functional block kinds (embedding / attention
  / norm / FFN / softmax …), drop the single-accent rule and use a
  desaturated pastel palette where each block kind has its own
  `{ fill, stroke, text }` triad. See
  [`templates/math-figure-transformer.canvas.tsx`](../templates/math-figure-transformer.canvas.tsx)
  for a worked example based on the original Transformer encoder–decoder
  architecture (Vaswani et al., 2017). Render at `760×620`.

  Guidelines for the categorical palette variant:
  - Keep all fills below ~80 % saturation. The figure should still read
    as one cohesive paper figure, not a brand-color collage.
  - Reuse the same hue family for related blocks (e.g. *Self-Attention*
    light blue → *Masked Attention* darker blue → *Cross-Attention*
    teal). Hue distance encodes functional distance.
  - Norm / residual wrapper blocks should be the **least saturated**
    color (warm gray works well) so they recede behind the operators
    they wrap.
  - Stroke and text are derived from the same hue as the fill, just
    darker — this keeps each block self-coherent under printing.
  - Use a single arrow color (`PAL.arrow`) regardless of block colors,
    and a single `<defs><marker id="arrow">` for all arrowheads.

## SVG adaptation notes

- This template **does not** call `useHostTheme()`. Paper figures must
  print on white regardless of host UI theme; the deviation from the rest
  of the canvas SDK is deliberate.
- Avoid more than ~120 SVG nodes total. The MLP defaults to 78 edges +
  19 circles + ~20 text elements = ~117 nodes, which renders crisply at
  the native 720×460 and prints cleanly at 2× scale.
- Do not embed raster images — keep this strictly vector so the figure
  scales under LaTeX `\includegraphics`.
- If you export PDF later, render to SVG first and pass through any
  SVG → PDF tool (`rsvg-convert`, Inkscape `--export-type=pdf`, etc.).
