// Code review primitives — DiffGroup, ReviewComment, ReviewThread, FileReview.
// Diff content is rendered as monospaced text rows with full-width strip
// fills for added / removed lines. No interaction (SVG is static).

import React from "react";
import { useHostTheme } from "./hooks.mjs";

const h = React.createElement;
const MONO = "SFMono-Regular, Menlo, Consolas, 'Courier New', monospace";

export function DiffGroup({ lines = [], x = 0, y = 0, width = 720, fontSize = 12 }) {
  const { tokens } = useHostTheme();
  const lineH = Math.round(fontSize * 1.6);
  const gutterW = 56;
  const totalH = lines.length * lineH + 8;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": totalH },
    h("rect", { x: 0, y: 0, width, height: totalH, rx: tokens.radius.md, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    lines.map((line, i) => renderDiffLine(line, i, { lineH, gutterW, fontSize, width, tokens }))
  );
}

function renderDiffLine(line, idx, { lineH, gutterW, fontSize, width, tokens }) {
  const ly = idx * lineH + 4;
  const kind = line.kind || "ctx";
  const stripFill =
    kind === "add" ? tokens.diff.insertedLine :
    kind === "del" ? tokens.diff.removedLine : "transparent";
  const sigil =
    kind === "add" ? "+" :
    kind === "del" ? "-" : " ";
  const textColor =
    kind === "add" ? tokens.diff.addedText :
    kind === "del" ? tokens.diff.deletedText : tokens.text.primary;
  return h(React.Fragment, { key: idx },
    kind !== "ctx" ? h("rect", { x: 0, y: ly, width, height: lineH, fill: stripFill }) : null,
    h("text", { x: 8,  y: ly + fontSize + 1, fontSize, fontFamily: MONO, fill: tokens.text.tertiary }, line.oldNo || ""),
    h("text", { x: 28, y: ly + fontSize + 1, fontSize, fontFamily: MONO, fill: tokens.text.tertiary }, line.newNo || ""),
    h("text", { x: gutterW - 12, y: ly + fontSize + 1, fontSize, fontFamily: MONO, fill: textColor, fontWeight: 700 }, sigil),
    h("text", { x: gutterW + 6,  y: ly + fontSize + 1, fontSize, fontFamily: MONO, fill: textColor }, line.text || ""),
  );
}

export function ReviewComment({ author = "AI", body, x = 0, y = 0, width = 480, tone = "info" }) {
  const { tokens } = useHostTheme();
  const palette = {
    info:    { bg: tokens.status.infoBg,    border: tokens.status.infoBorder,    accent: tokens.status.info },
    success: { bg: tokens.status.successBg, border: tokens.status.successBorder, accent: tokens.status.success },
    warning: { bg: tokens.status.warningBg, border: tokens.status.warningBorder, accent: tokens.status.warning },
    danger:  { bg: tokens.status.dangerBg,  border: tokens.status.dangerBorder,  accent: tokens.status.danger },
  }[tone] || { bg: tokens.fill.tertiary, border: tokens.stroke.tertiary, accent: tokens.text.tertiary };
  const lines = wrap(body || "", Math.floor((width - 32) / 6.4));
  const height = 32 + lines.length * 16 + 12;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: tokens.radius.md, fill: palette.bg, stroke: palette.border }),
    h("text", { x: 14, y: 18, fontSize: 12, fontWeight: 600, fill: palette.accent, fontFamily: "system-ui" }, author),
    lines.map((ln, i) =>
      h("text", { key: i, x: 14, y: 36 + i * 16, fontSize: 12, fill: tokens.text.primary, fontFamily: MONO }, ln)
    )
  );
}

export function ReviewThread({ comments = [], x = 0, y = 0, width = 480 }) {
  let cursor = 0;
  const items = comments.map((c, i) => {
    const node = ReviewComment({ author: c.author, body: c.body, tone: c.tone, x: 0, y: cursor, width });
    const lines = Math.max(1, wrap(c.body || "", Math.floor((width - 32) / 6.4)).length);
    const h_ = 32 + lines * 16 + 12 + 8;
    cursor += h_;
    return node;
  });
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": cursor }, items);
}

export function FileReview({ filePath, summary, lines = [], x = 0, y = 0, width = 760 }) {
  const { tokens } = useHostTheme();
  const headerH = summary ? 56 : 36;
  const diffH = lines.length * 19 + 8;
  const totalH = headerH + diffH;
  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": totalH },
    h("rect", { x: 0, y: 0, width, height: totalH, rx: tokens.radius.md, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    h("rect", { x: 0, y: 0, width, height: headerH, rx: tokens.radius.md, fill: tokens.fill.tertiary }),
    h("text", { x: 14, y: 22, fontSize: 12, fontWeight: 600, fill: tokens.text.primary, fontFamily: MONO }, filePath || ""),
    summary ? h("text", { x: 14, y: 42, fontSize: 11, fill: tokens.text.tertiary, fontFamily: "system-ui" }, summary) : null,
    h("line", { x1: 0, y1: headerH, x2: width, y2: headerH, stroke: tokens.stroke.tertiary }),
    h("g", { transform: `translate(0, ${headerH})` }, DiffGroup({ lines, width, fontSize: 11 })),
  );
}

export function diffAnchorKey(anchor) {
  if (!anchor) return "";
  return `${anchor.file || ""}:${anchor.line || 0}:${anchor.side || ""}`;
}

function wrap(text, perLine) {
  const words = String(text).split(/\s+/);
  const out = [];
  let curr = "";
  for (const w of words) {
    if (!curr) { curr = w; continue; }
    if ((curr + " " + w).length <= perLine) curr += " " + w;
    else { out.push(curr); curr = w; }
  }
  if (curr) out.push(curr);
  return out.length ? out : [""];
}
