---
name: canvas
description: "Token-driven Canvas to SVG or PNG. AI writes .canvas.tsx, the bundled CLI renders a static .svg (default) or .png (for IM channels) with no IDE or browser."
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
platforms: [linux, macos, windows]
prerequisites:
  binaries: [node>=18]
metadata:
  hermes:
    tags: [Canvas, SVG, Diagrams, Sequence, DesignSystem, CodeReview, Visualization]
    related_skills: [excalidraw, architecture-diagram, concept-diagrams]
---

# Canvas Skill — JSX to SVG, offline

Render token-driven visual artifacts directly to standalone SVG files. Authoring is React/JSX (`.canvas.tsx`); the included Node renderer compiles the tree and writes a `.svg`. No IDE, no preview server, no API keys.

This skill is a port of the Qoder Canvas framework (`~/.qoder/canvas/`) adapted to the Hermes "skill = filesystem only" model.

## When to use

- Sequence diagrams (auth flows, service call paths, queue handoffs)
- One-page design system specimens (colors, typography, components, spacing)
- One-page code review summaries (priority issues + diff evidence)
- Anything else that fits a one-page, token-styled, vector visual

For freehand whiteboard diagrams use `excalidraw`. For dark cloud/infra HTML diagrams use `architecture-diagram`. This skill is the right pick when you want a precise, themed, fully scriptable SVG.

## Output formats: SVG vs PNG

The primary output is **SVG** (vector, infinite zoom, embeddable in Markdown / HTML / docs). PNG is supported as a **secondary** output for channels that do not render SVG:

| Channel                                  | SVG works? | Use |
|------------------------------------------|------------|-----|
| Markdown files, README, websites, PDF    | yes        | `.svg` |
| Image viewers, browsers                  | yes        | `.svg` |
| DingTalk / WeChat / Feishu / Slack / Telegram image messages | **no**     | `.png` |
| Mail clients, screenshots, slides        | mixed      | `.png` is safer |

To emit PNG, give `-o` a `.png` filename (or pass `--format png`). PNG pixel dimensions equal the SVG `viewBox` exactly — no cropping. PNG rasterization tries three backends in order, automatically falling back if one is missing or fails:

| # | Backend         | Cost / deps                                  | Use case                                          |
|---|-----------------|----------------------------------------------|---------------------------------------------------|
| 1 | `@resvg/resvg-js` | npm dep, ~6 MB, in-process, no system deps  | **Default**. Fast (~50ms), container-friendly.    |
| 2 | Chrome headless | Chrome/Chromium binary on disk               | Fallback. Supports `<foreignObject>`, complex CSS.|
| 3 | `rsvg-convert`  | `apt-get install librsvg2-bin`               | Last resort. Lightweight system binary.           |

Set `CANVAS_PNG_BACKEND=resvg|chrome|rsvg-convert` to **force** one backend (skipping the fallback chain). For most uses leave it unset — the default order works.

### PNG backend setup

- **resvg (recommended)**: covered by `npm install` in this skill (declared in `optionalDependencies`). Pure Rust, no headless browser needed. Works out-of-the-box on every container.
- **Chrome headless**: see *Chrome lookup order* below. The hermes-agent Docker image already installs Playwright Chromium, so this works without extra packages.
- **rsvg-convert**: `apt-get install -y librsvg2-bin` (~3 MB).

### Chrome lookup order

`render.mjs` finds a Chrome / Chromium binary by walking this list in order:

1. `$CANVAS_CHROME_BIN` (explicit override)
2. Standard desktop installs:
   - macOS: `/Applications/Google Chrome.app/...`, `Chromium.app/...`
   - Linux: `/usr/bin/google-chrome`, `/usr/bin/chromium`, `/usr/bin/chromium-browser`, ...
   - Windows: `C:\Program Files\Google\Chrome\Application\chrome.exe`
3. `PATH` lookups for `google-chrome` / `chromium` / `chromium-browser`
4. **Playwright-managed Chromium**: `$PLAYWRIGHT_BROWSERS_PATH/chromium_headless_shell-<rev>/chrome-linux/headless_shell` (default root: `/opt/hermes/.playwright`); also `~/.cache/ms-playwright/`. This is what the hermes-agent Docker image installs via `npx playwright install --with-deps chromium --only-shell` — the `headless_shell` binary accepts the same `--screenshot=` flag as full Chrome, so PNG output works out-of-the-box inside the container with **no extra packages**.

Each invocation gets a private `--user-data-dir` under `.canvas-tmp/chrome-<random>/` and runs with `--no-sandbox --disable-features=Crashpad --disable-crash-reporter --disable-breakpad`, plus `HOME` / `XDG_*` / `TMPDIR` redirected to that same dir — safe for non-root containers and locked-down sandboxes.

## Setup

One-time install of node deps (inside this skill folder):

```bash
cd "$HERMES_HOME/skills/creative/canvas"
npm install --silent
```

`HERMES_HOME` defaults to `~/.hermes`. Skill ships with a `package.json`; only `react` plus `@babel/*` are required.

## Workflow

1. **Disambiguate first** — if the user's request does not clearly map to exactly one recipe, run the **Template selection protocol** below before writing any code.
2. **Pick a recipe** from `recipes/index.md` — every recipe declares `name`, `description`, layout rules, and a copyable TSX shape.
3. **Author** an output file `my-canvas.canvas.tsx` next to (or anywhere outside) this skill. Always import primitives from `qoder/canvas`.
4. **Render** to SVG:

```bash
node "$HERMES_HOME/skills/creative/canvas/scripts/render.mjs" \
  my-canvas.canvas.tsx -o my-canvas.svg --theme dark --width 1200
```

Open the generated `.svg` in any browser, image viewer, or paste into Markdown.

## CLI

```
render.mjs INPUT.canvas.tsx [-o OUT.{svg,png}] [--theme light|dark]
                            [--width N] [--height N] [--bg COLOR]
                            [--format svg|png|both] [--keep-svg]

  INPUT          path to a .canvas.tsx (or .canvas.jsx) authoring file
  -o, --out      output path; extension chooses format (.svg default, .png also OK)
  --theme        theme tokens (default: light)
  --width        viewBox width  (default: 1200)
  --height       viewBox height (default: auto, padded around content)
  --format       force output kind (svg | png | both); overrides -o extension
  --keep-svg     when emitting png, also keep the intermediate .svg next to it
```

Examples:

```bash
# Default — SVG, embed in Markdown / docs.
node scripts/render.mjs my.canvas.tsx -o my.svg

# PNG only — ready to drop into DingTalk / WeChat / Feishu.
node scripts/render.mjs my.canvas.tsx -o my.png --width 1100 --height 1200

# Both — keep the vector master and a ready-to-send raster sidecar.
node scripts/render.mjs my.canvas.tsx -o my.svg --format both --width 1100 --height 1200
```

## Template selection protocol

The templates differ much more in *visual style* than in *content shape*, so a
text-only description is often not enough to choose. **When the request is
ambiguous about which template fits, you MUST ask the user before generating
any SVG.** Do not silently pick.

A request is *ambiguous* if any of these are true:

- The user said something generic like "draw a diagram / make a chart / 画一张图"
  without naming a recipe, a layout, or a visual style.
- Two or more templates could plausibly match the topic
  (e.g. "explain this algorithm" → `math-poster` *or* `math-figure` *or*
  `math-figure-transformer`; "document my system" → `design-system` *or*
  `sequence-diagram` *or* `code-review`).
- The user mentioned a topic but no style cue ("poster", "paper figure",
  "colorful", "timeline", "swatch", "review"…).

When ambiguous, ask **one question** that lists the candidate templates and,
for each candidate, **link the corresponding preview image** from
`examples/*.svg.png`. Use this exact format (Markdown image links so the
images render inline in the chat):

```
请帮我确认要用哪种风格（每个示例图就是这个模板的真实输出）：

1. <recipe-name> — <one line on what it is good for>
   ![<recipe-name>](examples/<recipe-name>.svg.png)

2. ...
```

Preview images bundled with this skill (always link the absolute path under
`$HERMES_HOME/skills/creative/canvas/examples/`):

| Template | Preview |
|----------|---------|
| `sequence-diagram`        | `examples/sequence-diagram.svg.png`        |
| `design-system` (light)   | `examples/design-system.svg.png`           |
| `design-system` (dark)    | `examples/design-system-dark.svg.png`      |
| `code-review`             | `examples/code-review.svg.png`             |
| `math-poster`             | `examples/math-poster.svg.png`             |
| `math-figure`             | `examples/math-figure.svg.png`             |
| `math-figure-transformer` | `examples/math-figure-transformer.svg.png` |

Guidelines for the question:

- **2–4 candidates max.** Filter by topic before asking; don't dump all 7.
- **Show the preview image inline**, not just the filename — the picture is
  the disambiguator, not the prose.
- **Allow free-form override** ("也可以告诉我你想要的别的风格 / 自定义
spec").
- **Do not start rendering** until the user replies. If the user says
  "随便" or "你定", default to the template with the closest topical match
  and tell the user which one you picked and why before rendering.

A request is **not** ambiguous, and you should skip the question, when:

- The user names the recipe explicitly ("用 math-poster", "sequence diagram
for login").
- The user passes a `.canvas.tsx` file or a recipe id.
- The topic uniquely fixes the template (e.g. "PR review" → `code-review`,
  "design tokens cheat sheet" → `design-system`).

## Templates and recipes

- `templates/sequence-diagram.canvas.tsx` — minimal 4-lane flow, runs out of the box.
- `templates/design-system.canvas.tsx` — color, typography, button, card specimen.
- `templates/code-review.canvas.tsx` — single-page review with prioritized issues + diff.
- `templates/math-poster.canvas.tsx` — academic-poster-styled algorithm/theorem explainer (full-page narrative; self-contained navy/burgundy/mustard palette).
- `templates/math-figure.canvas.tsx` — paper-figure-scale single illustration (default: MLP architecture diagram with caption).
- `templates/math-figure-transformer.canvas.tsx` — paper-figure-scale architecture diagram with categorical color palette (default: Transformer encoder–decoder).
- `recipes/*.recipe.md` — layout rules, content shape, SVG adaptation notes.
- `references/tokens-cheatsheet.md` — every token path and hex value (light + dark).

## Output Format

A self-contained `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" width width height height>...</svg>`. Inline fonts default to system-ui / SFMono-Regular fallbacks; no external font fetch.

## Verification

```bash
cd "$HERMES_HOME/skills/creative/canvas"
node scripts/render.mjs templates/sequence-diagram.canvas.tsx -o /tmp/seq.svg
node scripts/render.mjs templates/design-system.canvas.tsx   -o /tmp/ds.svg  --theme light
node scripts/render.mjs templates/code-review.canvas.tsx     -o /tmp/cr.svg
node scripts/render.mjs templates/math-poster.canvas.tsx     -o /tmp/mp.svg --width 1100 --height 1200
node scripts/render.mjs templates/math-figure.canvas.tsx     -o /tmp/mf.svg --width 720  --height 460
node scripts/render.mjs templates/math-figure-transformer.canvas.tsx -o /tmp/mft.svg --width 760 --height 620
```

Each run should exit 0 and write a non-empty `.svg`.

To refresh the preview PNGs under `examples/` (full-aspect-ratio screenshots
rendered via Chrome headless, used by the *Template selection protocol*):

```bash
bash scripts/render-previews.sh
```

Each `examples/<name>.svg` will get a matching `examples/<name>.svg.png` whose
pixel dimensions equal the SVG `viewBox` exactly (no square-thumbnail cropping).

## Rules

- Always import from `qoder/canvas`. The renderer rewrites this specifier to the bundled SDK.
- Only use color paths declared in `references/tokens-cheatsheet.md` (or `useHostTheme().tokens`). Do not hard-code hex unless authoring a `design-system` swatch.
- Stack/Row/Grid use additive layout (no flex). Children must declare width/height; semantic primitives (Card, Stat, Button) provide sane defaults.
- Output is one vertical page. Do not author multi-screen tabs or sidebars — there is nothing to drive them at runtime.
- Translate visible UI text to the user's language. Keep file paths, code, and identifiers unchanged.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot find module 'react'` | Run `npm install` inside this skill folder. |
| `SyntaxError` in .canvas.tsx | Ensure file ends with `.canvas.tsx` or `.canvas.jsx`; renderer auto-detects via extension. |
| Empty SVG | Check that the default export is a function returning JSX. The renderer ignores files without a default export. |
| Wrong colors | Set `--theme dark` or `--theme light`; confirm token paths against `references/tokens-cheatsheet.md`. |
| `PNG output failed in all backends` | Either `npm install` inside this skill (gives you `@resvg/resvg-js`, which has no system deps), or install Chrome/Chromium and set `CANVAS_CHROME_BIN`, or `apt-get install -y librsvg2-bin` for `rsvg-convert`. The error message lists what each backend tried. |
| `PNG output requires Chrome/Chromium` | Only seen when `CANVAS_PNG_BACKEND=chrome` is forced. Install Google Chrome, or `export CANVAS_CHROME_BIN=/path/to/chrome`. In containers, ensure `PLAYWRIGHT_BROWSERS_PATH` points to a tree that contains `chromium_headless_shell-*/chrome-linux/headless_shell` (hermes-agent's Dockerfile already sets this up). |
| PNG looks cropped / square | You're looking at an old `qlmanage` thumbnail. Re-emit with `node scripts/render.mjs ... -o foo.png` — it always matches the SVG `viewBox` 1:1. |
