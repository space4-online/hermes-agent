// Core primitives — minimal SVG implementations of the Qoder canvas components.
// Each component accepts an optional { x, y } and a "width"/"height" for layout.
// Containers (Stack/Row/Grid/Card) lay out their children additively (no flex).

import React from "react";
import { useHostTheme } from "./hooks.mjs";
import { estimateTextWidth } from "../runtime/layout.mjs";

const h = React.createElement;

// ---------- helpers ----------

function trans(x, y, body) {
  if (!x && !y) return h(React.Fragment, null, body);
  return h("g", { transform: `translate(${x || 0}, ${y || 0})` }, body);
}

function clampWidth(w, min = 60) { return Math.max(min, w | 0); }

// ---------- containers ----------

export function Stack({ children, gap = 12, padding = 0, width = 0, x = 0, y = 0, background, border, radius = 0 }) {
  const { tokens } = useHostTheme();
  const list = React.Children.toArray(children).filter(Boolean);
  const items = [];
  let cursor = padding;
  let maxW = width;
  for (const child of list) {
    const ch = pickHeight(child, 24);
    const cw = pickWidth(child, width || 200);
    if (!width) maxW = Math.max(maxW, cw + padding * 2);
    items.push(trans(padding, cursor, child));
    cursor += ch + gap;
  }
  const totalH = Math.max(0, cursor - gap) + padding;
  const w = width || maxW;
  const bgRect = (background || border)
    ? h("rect", {
        x: 0, y: 0, width: w, height: totalH, rx: radius, ry: radius,
        fill: background || "none",
        stroke: border || "none",
      })
    : null;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": w, "data-h": totalH },
    bgRect, ...items);
}

export function Row({ children, gap = 12, padding = 0, height = 0, x = 0, y = 0, align = "start" }) {
  const list = React.Children.toArray(children).filter(Boolean);
  const items = [];
  let cursor = padding;
  let maxH = height;
  for (const child of list) {
    const cw = pickWidth(child, 80);
    const ch = pickHeight(child, 24);
    if (!height) maxH = Math.max(maxH, ch);
    let dy = padding;
    if (align === "center") dy = padding + Math.max(0, ((height || maxH) - ch) / 2);
    if (align === "end")    dy = padding + Math.max(0, ((height || maxH) - ch));
    items.push(trans(cursor, dy, child));
    cursor += cw + gap;
  }
  const totalW = Math.max(0, cursor - gap) + padding;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": totalW, "data-h": height || maxH },
    ...items);
}

export function Grid({ children, columns = 3, gapX = 16, gapY = 16, columnWidth = 240, rowHeight = 80, x = 0, y = 0 }) {
  const list = React.Children.toArray(children).filter(Boolean);
  const items = list.map((child, i) => {
    const col = i % columns;
    const row = Math.floor(i / columns);
    return trans(col * (columnWidth + gapX), row * (rowHeight + gapY), child);
  });
  const totalW = columns * columnWidth + (columns - 1) * gapX;
  const totalRows = Math.ceil(list.length / columns);
  const totalH = totalRows * rowHeight + Math.max(0, totalRows - 1) * gapY;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": totalW, "data-h": totalH }, ...items);
}

export function Divider({ width = 0, color, x = 0, y = 0 }) {
  const { tokens } = useHostTheme();
  return h("line", {
    x1: x, y1: y, x2: x + (width || 200), y2: y,
    stroke: color || tokens.stroke.tertiary,
    strokeWidth: 1,
    "data-h": 1,
    "data-w": width || 200,
  });
}

export function Spacer({ size = 8 }) {
  return h("g", { "data-w": size, "data-h": size });
}

// ---------- text ----------

function _Text({ children, x = 0, y = 0, fontSize = 13, fontWeight = 400, color, fontFamily, anchor = "start", letterSpacing }) {
  const { tokens } = useHostTheme();
  const lh = Math.round(fontSize * 1.45);
  return h("text", {
    x, y: y + Math.round(fontSize * 0.85),
    fill: color || tokens.text.primary,
    fontFamily: fontFamily || "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
    fontSize,
    fontWeight,
    textAnchor: anchor === "middle" ? "middle" : anchor === "end" ? "end" : "start",
    letterSpacing,
    "data-h": lh,
  }, String(children == null ? "" : children));
}
export const Text = _Text;

export function H1(props) { return _Text({ fontSize: 24, fontWeight: 700, ...props }); }
export function H2(props) { return _Text({ fontSize: 18, fontWeight: 650, ...props }); }
export function H3(props) { return _Text({ fontSize: 14, fontWeight: 600, ...props }); }

export function Code({ children, x = 0, y = 0, fontSize = 12, color }) {
  const { tokens } = useHostTheme();
  return h("text", {
    x, y: y + Math.round(fontSize * 0.85),
    fill: color || tokens.text.primary,
    fontFamily: "SFMono-Regular, Menlo, Consolas, 'Courier New', monospace",
    fontSize,
    "data-h": Math.round(fontSize * 1.5),
  }, String(children == null ? "" : children));
}

export function Link({ children, x = 0, y = 0, fontSize = 13 }) {
  const { tokens } = useHostTheme();
  return _Text({ children, x, y, fontSize, color: tokens.text.link });
}

// ---------- card ----------

export function Card({ children, width = 320, height = 120, padding = 16, x = 0, y = 0, tone = "neutral", radius, accent }) {
  const { tokens } = useHostTheme();
  const r = radius != null ? radius : tokens.radius.md;
  const fill = tokens.bg.elevated;
  const stroke = tokens.stroke.tertiary;
  const accentBar = accent
    ? h("rect", { x: 0, y: 0, width: 4, height, fill: accent, rx: 0 })
    : null;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: r, ry: r, fill, stroke }),
    accentBar,
    trans(padding, padding, children),
  );
}

export function CardHeader({ title, subtitle, width = 320, x = 0, y = 0 }) {
  const { tokens } = useHostTheme();
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": subtitle ? 44 : 24 },
    _Text({ children: title, fontSize: 14, fontWeight: 600, color: tokens.text.primary }),
    subtitle ? _Text({ children: subtitle, y: 22, fontSize: 12, color: tokens.text.tertiary }) : null,
  );
}

export function CardBody({ children, x = 0, y = 0 }) {
  return trans(x, y, children);
}

export function CollapsibleCard(props) { return Card(props); }

// ---------- buttons ----------

export function Button({ label, variant = "primary", x = 0, y = 0, width, height = 32, onClick }) {
  const { tokens } = useHostTheme();
  const styles = {
    primary:   { bg: tokens.accent.control, fg: tokens.text.onAccent, stroke: tokens.accent.control },
    secondary: { bg: tokens.fill.secondary,  fg: tokens.text.primary,  stroke: tokens.stroke.tertiary },
    ghost:     { bg: "none",                 fg: tokens.text.primary,  stroke: "none" },
    danger:    { bg: tokens.status.danger,   fg: "#fff",               stroke: tokens.status.danger },
  };
  const s = styles[variant] || styles.primary;
  const w = width || clampWidth(estimateTextWidth(label, 13) + 28);
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": w, "data-h": height },
    h("rect", { x: 0, y: 0, width: w, height, rx: 6, ry: 6, fill: s.bg, stroke: s.stroke }),
    _Text({ children: label, x: w / 2, y: (height - 13) / 2, anchor: "middle", color: s.fg, fontSize: 13, fontWeight: 500 }),
  );
}

export function SendToChatButton({ label = "Send to Chat", ...rest }) {
  return Button({ label, variant: "secondary", ...rest });
}

export function IconButton({ label = "·", variant = "ghost", x = 0, y = 0, size = 28 }) {
  return Button({ label, variant, x, y, width: size, height: size });
}

// ---------- tags / pills ----------

export function Tag({ label, tone = "neutral", x = 0, y = 0 }) {
  const { tokens } = useHostTheme();
  const palette = tonePalette(tokens, tone);
  const w = clampWidth(estimateTextWidth(label, 11) + 16, 36);
  const height = 20;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": w, "data-h": height },
    h("rect", { x: 0, y: 0, width: w, height, rx: 10, ry: 10, fill: palette.bg, stroke: palette.border }),
    _Text({ children: label, x: w / 2, y: 4, anchor: "middle", color: palette.fg, fontSize: 11, fontWeight: 500 }),
  );
}

export function Pill({ label, tone = "neutral", x = 0, y = 0 }) {
  return Tag({ label, tone, x, y });
}

function tonePalette(tokens, tone) {
  const map = {
    neutral: { bg: tokens.fill.tertiary,    fg: tokens.text.secondary, border: tokens.stroke.tertiary },
    info:    { bg: tokens.status.infoBg,    fg: tokens.status.info,    border: tokens.status.infoBorder },
    success: { bg: tokens.status.successBg, fg: tokens.status.success, border: tokens.status.successBorder },
    warning: { bg: tokens.status.warningBg, fg: tokens.status.warning, border: tokens.status.warningBorder },
    danger:  { bg: tokens.status.dangerBg,  fg: tokens.status.danger,  border: tokens.status.dangerBorder },
    accent:  { bg: tokens.primary.bg,       fg: tokens.primary.text,   border: tokens.primary.border },
  };
  return map[tone] || map.neutral;
}

// ---------- form (visual only) ----------

export function Input({ value = "", placeholder = "", x = 0, y = 0, width = 200, height = 28 }) {
  const { tokens } = useHostTheme();
  const display = value || placeholder;
  const color = value ? tokens.text.primary : tokens.text.tertiary;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: 6, ry: 6, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    _Text({ children: display, x: 10, y: (height - 13) / 2, fontSize: 12, color }),
  );
}

export function TextArea({ value = "", placeholder = "", x = 0, y = 0, width = 280, height = 80 }) {
  const { tokens } = useHostTheme();
  const display = value || placeholder;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: 6, ry: 6, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    _Text({ children: display, x: 10, y: 8, fontSize: 12, color: value ? tokens.text.primary : tokens.text.tertiary }),
  );
}

export function Checkbox({ checked = false, label, x = 0, y = 0 }) {
  const { tokens } = useHostTheme();
  const box = h("rect", { x: 0, y: 4, width: 14, height: 14, rx: 3, ry: 3,
    fill: checked ? tokens.accent.control : tokens.bg.elevated,
    stroke: checked ? tokens.accent.control : tokens.stroke.secondary });
  const tick = checked ? h("path", { d: "M3 10 L 6 13 L 12 6", fill: "none",
    stroke: tokens.text.onAccent, strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round",
    transform: "translate(0, 4)" }) : null;
  const lbl = label ? _Text({ children: label, x: 22, y: 4, fontSize: 12, color: tokens.text.primary }) : null;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": 14 + (label ? 22 + estimateTextWidth(label, 12) : 0), "data-h": 22 },
    box, tick, lbl);
}

export function Switch({ on = false, x = 0, y = 0 }) {
  const { tokens } = useHostTheme();
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": 32, "data-h": 18 },
    h("rect", { x: 0, y: 0, width: 32, height: 18, rx: 9, ry: 9,
      fill: on ? tokens.accent.control : tokens.fill.tertiary,
      stroke: on ? tokens.accent.control : tokens.stroke.tertiary }),
    h("circle", { cx: on ? 23 : 9, cy: 9, r: 7, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
  );
}

export function Select({ value = "", x = 0, y = 0, width = 200, height = 28 }) {
  const { tokens } = useHostTheme();
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: 6, ry: 6, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    _Text({ children: value || "Select…", x: 10, y: (height - 13) / 2, fontSize: 12, color: tokens.text.primary }),
    h("path", { d: `M ${width - 14} ${height / 2 - 2} l 5 6 l 5 -6`, stroke: tokens.text.tertiary, strokeWidth: 1.5, fill: "none" }),
  );
}

// ---------- table ----------

export function Table({ columns = [], rows = [], width = 720, x = 0, y = 0, density = "comfortable" }) {
  const { tokens } = useHostTheme();
  const rowH = density === "compact" ? 26 : 34;
  const headH = 28;
  const colCount = Math.max(1, columns.length);
  const flexCols = columns.map(c => (typeof c === "object" ? c : { key: c, header: c }));
  const colW = Math.floor(width / colCount);
  const totalH = headH + rows.length * rowH;
  const headerCells = flexCols.map((c, i) =>
    _Text({ children: c.header, x: i * colW + 12, y: 8, fontSize: 11, fontWeight: 600, color: tokens.text.tertiary })
  );
  const bodyRows = rows.map((row, ri) => {
    const cells = flexCols.map((c, ci) => {
      const v = row[c.key];
      return _Text({ children: v == null ? "" : v, x: ci * colW + 12, y: ri * rowH + headH + 8, fontSize: 12, color: tokens.text.primary });
    });
    const stripe = ri % 2 === 1 ? h("rect", { x: 0, y: ri * rowH + headH, width, height: rowH, fill: tokens.fill.quaternary }) : null;
    return h(React.Fragment, { key: ri }, stripe, ...cells);
  });
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": totalH },
    h("rect", { x: 0, y: 0, width, height: totalH, rx: tokens.radius.md, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    h("rect", { x: 0, y: 0, width, height: headH, fill: tokens.fill.tertiary, rx: tokens.radius.md }),
    h("line", { x1: 0, y1: headH, x2: width, y2: headH, stroke: tokens.stroke.tertiary }),
    ...headerCells,
    ...bodyRows,
  );
}

export const TableRow = ({ children }) => h(React.Fragment, null, children);
export const TableCell = ({ children, x = 0, y = 0 }) => trans(x, y, children);

// ---------- stats / progress / delta / callout / banner ----------

export function Delta({ value, direction = "up", x = 0, y = 0 }) {
  const { tokens } = useHostTheme();
  const color = direction === "up" ? tokens.status.success : direction === "down" ? tokens.status.danger : tokens.text.tertiary;
  const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : "→";
  return _Text({ children: `${arrow} ${value}`, x, y, fontSize: 12, color, fontWeight: 600 });
}

export function Progress({ value = 0, max = 100, x = 0, y = 0, width = 200, height = 6, tone = "info" }) {
  const { tokens } = useHostTheme();
  const ratio = Math.max(0, Math.min(1, value / max));
  const palette = tonePalette(tokens, tone);
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: height / 2, ry: height / 2, fill: tokens.fill.tertiary }),
    h("rect", { x: 0, y: 0, width: ratio * width, height, rx: height / 2, ry: height / 2, fill: palette.fg }),
  );
}

export function Stat({ label, value, delta, x = 0, y = 0, width = 200, height = 80 }) {
  const { tokens } = useHostTheme();
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: tokens.radius.md, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    _Text({ children: label, x: 14, y: 12, fontSize: 11, color: tokens.text.tertiary, fontWeight: 600 }),
    _Text({ children: value, x: 14, y: 30, fontSize: 22, fontWeight: 650, color: tokens.text.primary }),
    delta ? Delta({ value: delta.value, direction: delta.direction, x: 14, y: 60 }) : null,
  );
}

export function Callout({ title, body, tone = "info", x = 0, y = 0, width = 480 }) {
  const { tokens } = useHostTheme();
  const palette = tonePalette(tokens, tone);
  const bodyLines = wrapLines(body || "", Math.floor((width - 36) / 6));
  const height = 28 + bodyLines.length * 18 + 16;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: tokens.radius.md, fill: palette.bg, stroke: palette.border }),
    h("rect", { x: 0, y: 0, width: 4, height, fill: palette.fg }),
    _Text({ children: title, x: 16, y: 12, fontSize: 13, fontWeight: 600, color: palette.fg }),
    ...bodyLines.map((line, i) => _Text({ children: line, x: 16, y: 32 + i * 18, fontSize: 12, color: tokens.text.primary })),
  );
}

export function Banner({ title, tone = "info", x = 0, y = 0, width = 720 }) {
  const { tokens } = useHostTheme();
  const palette = tonePalette(tokens, tone);
  const height = 36;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: tokens.radius.md, fill: palette.bg, stroke: palette.border }),
    _Text({ children: title, x: 16, y: 12, fontSize: 13, fontWeight: 600, color: palette.fg }),
  );
}

export function Skeleton({ width = 120, height = 12, x = 0, y = 0 }) {
  const { tokens } = useHostTheme();
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: 4, fill: tokens.fill.tertiary }),
  );
}

// ---------- internal helpers ----------

function pickWidth(child, fallback) {
  if (!child || typeof child !== "object" || !child.props) return fallback;
  const { width, w, ["data-w"]: dw } = child.props;
  return Number(width) || Number(w) || Number(dw) || fallback;
}
function pickHeight(child, fallback) {
  if (!child || typeof child !== "object" || !child.props) return fallback;
  const { height, h: hh, ["data-h"]: dh } = child.props;
  return Number(height) || Number(hh) || Number(dh) || fallback;
}

function wrapLines(text, perLine) {
  const words = String(text).split(/\s+/);
  const lines = [];
  let current = "";
  for (const w of words) {
    if (!current) { current = w; continue; }
    if ((current + " " + w).length <= perLine) current += " " + w;
    else { lines.push(current); current = w; }
  }
  if (current) lines.push(current);
  return lines.length ? lines : [""];
}
