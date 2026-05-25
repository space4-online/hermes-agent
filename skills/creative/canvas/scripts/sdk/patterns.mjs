// Patterns — semantic building blocks (Timeline, MetricsGrid, RiskCallout,
// RiskHeatmap, ReferencePanel, DocsSection). Compose primitives so authoring
// stays terse.

import React from "react";
import { useHostTheme } from "./hooks.mjs";
import { Stat, Callout } from "./primitives.mjs";

const h = React.createElement;
const FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";

export function MetricsGrid({ items = [], columns = 4, x = 0, y = 0, width = 960 }) {
  const gap = 12;
  const cellW = (width - gap * (columns - 1)) / columns;
  const cellH = 80;
  const rows = Math.ceil(items.length / columns);
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": rows * cellH + (rows - 1) * gap },
    items.map((item, i) => {
      const col = i % columns;
      const row = Math.floor(i / columns);
      return h("g", { key: i, transform: `translate(${col * (cellW + gap)}, ${row * (cellH + gap)})` },
        Stat({ label: item.label, value: item.value, delta: item.delta, width: cellW, height: cellH })
      );
    })
  );
}

export function Timeline({ events = [], x = 0, y = 0, width = 720 }) {
  const { tokens } = useHostTheme();
  const rowH = 56;
  const dotX = 18;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": events.length * rowH },
    h("line", { x1: dotX, y1: 8, x2: dotX, y2: events.length * rowH - 8, stroke: tokens.stroke.tertiary }),
    events.map((e, i) =>
      h("g", { key: i, transform: `translate(0, ${i * rowH})` },
        h("circle", { cx: dotX, cy: 14, r: 6, fill: e.color || tokens.accent.control, stroke: tokens.bg.editor, strokeWidth: 2 }),
        h("text", { x: dotX + 18, y: 18, fontSize: 13, fontWeight: 600, fill: tokens.text.primary, fontFamily: FONT }, e.title || ""),
        h("text", { x: dotX + 18, y: 36, fontSize: 11, fill: tokens.text.tertiary, fontFamily: FONT }, e.timestamp || ""),
        e.body ? h("text", { x: dotX + 18, y: 50, fontSize: 12, fill: tokens.text.secondary, fontFamily: FONT }, e.body) : null,
      )
    )
  );
}

export function RiskCallout({ title, body, severity = "warning", x = 0, y = 0, width = 480 }) {
  return Callout({ title, body, tone: severity, x, y, width });
}

export function RiskHeatmap({ cells = [], cols = 5, rows = 5, x = 0, y = 0, cellSize = 36, gap = 4 }) {
  const { tokens } = useHostTheme();
  const palette = {
    none: tokens.fill.tertiary,
    low: tokens.status.successBg,
    medium: tokens.status.warningBg,
    high: tokens.status.dangerBg,
    critical: tokens.status.danger,
  };
  const totalW = cols * cellSize + (cols - 1) * gap;
  const totalH = rows * cellSize + (rows - 1) * gap;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": totalW, "data-h": totalH },
    cells.map((c, i) => {
      const cx = c.col * (cellSize + gap);
      const cy = c.row * (cellSize + gap);
      const fill = palette[c.level] || palette.none;
      return h(React.Fragment, { key: i },
        h("rect", { x: cx, y: cy, width: cellSize, height: cellSize, rx: 4, fill,
          stroke: c.level === "critical" ? tokens.status.dangerBorder : tokens.stroke.tertiary }),
        c.label ? h("text", { x: cx + cellSize / 2, y: cy + cellSize / 2 + 4,
          fontSize: 11, textAnchor: "middle", fill: tokens.text.primary, fontFamily: FONT }, c.label) : null,
      );
    })
  );
}

export function ReferencePanel({ title = "References", items = [], x = 0, y = 0, width = 320 }) {
  const { tokens } = useHostTheme();
  const rowH = 22;
  const padding = 14;
  const height = padding * 2 + 22 + items.length * rowH;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: tokens.radius.md, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    h("text", { x: padding, y: padding + 12, fontSize: 12, fontWeight: 600, fill: tokens.text.primary, fontFamily: FONT }, title),
    items.map((item, i) =>
      h("text", { key: i, x: padding, y: padding + 32 + i * rowH, fontSize: 12,
        fill: item.kind === "file" ? tokens.text.link : tokens.text.secondary, fontFamily: "SFMono-Regular, monospace" },
        `${item.kind ? `[${item.kind}] ` : ""}${item.label || item.path || ""}`),
    )
  );
}

export function DocsSection({ title, children, x = 0, y = 0, width = 720 }) {
  const { tokens } = useHostTheme();
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width },
    h("text", { x: 0, y: 16, fontSize: 11, fontWeight: 700, fill: tokens.text.tertiary, letterSpacing: "0.08em", fontFamily: FONT },
      String(title || "").toUpperCase()),
    h("line", { x1: 0, y1: 24, x2: width, y2: 24, stroke: tokens.stroke.tertiary }),
    h("g", { transform: "translate(0, 36)" }, children),
  );
}
