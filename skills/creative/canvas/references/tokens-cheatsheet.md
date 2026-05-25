# Tokens cheatsheet

Every value below is read at render time from `useHostTheme().tokens`. Both
`light` (default) and `dark` themes expose **identical structure**, so the same
component code renders correctly in either mode.

## bg — surface backgrounds

| key            | light     | dark      | use for |
|----------------|-----------|-----------|---------|
| `bg.editor`    | `#ffffff` | `#0d1117` | full-canvas background, sets `--bg` |
| `bg.chrome`    | `#f6f8fa` | `#010409` | toolbar / header chrome |
| `bg.elevated`  | `#ffffff` | `#161b22` | cards, modals, callouts |
| `bg.sidebar`   | `#f6f8fa` | `#010409` | navigation panels |
| `bg.panel`     | `#ffffff` | `#0d1117` | secondary panels |
| `bg.overlay`   | `rgba(15,23,42,0.45)` | `rgba(2,6,23,0.6)` | modal scrims |
| `bg.highlight` | `#fff8c5` | `#3a2c0c` | search hit / selection emphasis |

## text

| key                | light     | dark      |
|--------------------|-----------|-----------|
| `text.primary`     | `#1f2328` | `#e6edf3` |
| `text.secondary`   | `#4b5563` | `#9ba8b4` |
| `text.tertiary`    | `#6e7781` | `#7d8590` |
| `text.quaternary`  | `#9ca3af` | `#6e7681` |
| `text.link`        | `#0969da` | `#58a6ff` |
| `text.onAccent`    | `#ffffff` | `#0d1117` |

## stroke

| key                 | light     | dark      | use for |
|---------------------|-----------|-----------|---------|
| `stroke.primary`    | `#1f2328` | `#e6edf3` | high-contrast outlines |
| `stroke.secondary`  | `#6e7781` | `#7d8590` | secondary outlines |
| `stroke.tertiary`   | `#d0d7de` | `#30363d` | default card / divider lines |
| `stroke.quaternary` | `#eaeef2` | `#21262d` | subtle table rows |

## fill

| key                | light     | dark      | use for |
|--------------------|-----------|-----------|---------|
| `fill.primary`     | `#1f2328` | `#e6edf3` | foreground glyphs |
| `fill.secondary`   | `#f6f8fa` | `#161b22` | secondary buttons |
| `fill.tertiary`    | `#eaeef2` | `#21262d` | tag pill default bg, table head |
| `fill.quaternary`  | `#f6f8fa` | `#161b22` | row stripes |
| `fill.disable`     | `#e5e7eb` | `#21262d` | disabled controls |

## accent / primary

| key                       | light     | dark      |
|---------------------------|-----------|-----------|
| `accent.primary`          | `#0969da` | `#58a6ff` |
| `accent.control`          | `#0969da` | `#58a6ff` |
| `accent.controlHover`     | `#0860c4` | `#79c0ff` |
| `primary.color`           | `#0969da` | `#58a6ff` |
| `primary.bg` / `bgHover`  | `#ddf4ff` / `#b6e3ff` | `#0d2138` / `#10294a` |
| `primary.border`          | `#80ccff` | `#1f5fa0` |
| `primary.onPrimary`       | `#ffffff` | `#0d1117` |

## status (= tone)

Each status family has 5 keys: `<name>`, `<name>Hover`, `<name>Bg`, `<name>BgHover`, `<name>Border`.

| family    | foreground (light/dark) | bg (light/dark) |
|-----------|-------------------------|-----------------|
| `success` | `#1a7f37` / `#3fb950`   | `#dafbe1` / `#0f2e1a` |
| `warning` | `#9a6700` / `#d29922`   | `#fff8c5` / `#3a2c0c` |
| `danger`  | `#cf222e` / `#f85149`   | `#ffebe9` / `#2d0f10` |
| `info`    | `#0969da` / `#58a6ff`   | `#ddf4ff` / `#0d2138` |

`tokens.tone.*` is an alias for `tokens.status.*` and exists for parity with
the original Qoder SDK.

## diff (code review)

| key                  | light     | dark      |
|----------------------|-----------|-----------|
| `diff.insertedLine`  | `#dafbe1` | `#0f2e1a` |
| `diff.removedLine`   | `#ffebe9` | `#2d0f10` |
| `diff.stripAdded`    | `#aceebb` | `#1f6f3f` |
| `diff.stripRemoved`  | `#ffaba8` | `#762d2d` |
| `diff.added`         | `#1a7f37` | `#3fb950` |
| `diff.deleted`       | `#cf222e` | `#f85149` |
| `diff.addedText`     | `#0a3a14` | `#aff5b4` |
| `diff.deletedText`   | `#67060c` | `#ffa198` |

## syntax (code highlighting)

`tokens.syntax.{keyword, string, number, comment, type, fn, punct, property, regex, plain}`

## chart

`tokens.chart.{blue, lightBlue, teal, cyan, green, lightGreen, brightOrange, deepOrange, goldenYellow, darkAmber, red, purple, violet, warmPink, warmPeach, brown, muted, neutralLine, sequence}`

`sequence` is an 8-color array for cyclic series picks.

## radius / shadow / spacing / fontSize / motion / typography

| group        | example keys                                             |
|--------------|-----------------------------------------------------------|
| `radius`     | `none`, `xs`, `sm`, `md` (= 6), `lg`, `xl`, `full`        |
| `shadow`     | `sm`, `md`, `lg`                                          |
| `spacing`    | `0.5..10` (numeric, 1 = 4 px)                             |
| `fontSize`   | `xs..6xl` (string with `px`)                              |
| `motion`     | `durationFast/Base/Slow`, `easeIn/Out/InOut/Linear`       |
| `typography` | `body`, `small`, `h1`, `h2`, `h3`, `mono`                 |

## How to switch theme

```bash
node scripts/render.mjs templates/design-system.canvas.tsx --theme dark
```

Programmatically (inside a custom CLI):

```js
import { applyTheme } from "./scripts/sdk/hooks.mjs";
applyTheme("dark");
```

`applyTheme()` is module-level. Call it **before** invoking the React component
and once per render pass.
