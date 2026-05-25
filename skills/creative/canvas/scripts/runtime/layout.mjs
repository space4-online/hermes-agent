// Layout helpers shared by primitives.
// SVG has no flex; Stack/Row simply translate their children sequentially.
// Each child must declare a "height" or "width" prop; missing values fall
// back to a sensible default per primitive (defined in primitives.mjs).

import React from "react";

/**
 * Estimate text width for monospace / sans fallbacks. Hand-tuned average
 * advance per character at the given font-size. Used for badge widths and
 * Card title sizing. Not pixel-perfect; SVG renderers may shift slightly.
 */
export function estimateTextWidth(text, fontSize = 13, mono = false) {
  const advance = mono ? fontSize * 0.6 : fontSize * 0.55;
  return Math.max(0, String(text || "").length * advance);
}

/**
 * Walk children, compute child layout boxes, and emit a single <g>.
 * Each child either:
 *   - is a function-component element with explicit `height` / `width` prop, or
 *   - is a primitive that returns a <g> with `data-h` / `data-w` annotation.
 * Missing dimensions take fallback (`fallback`).
 */
export function stackChildren(children, { gap = 8, axis = "y", fallback = 24 }) {
  const list = React.Children.toArray(children).filter(Boolean);
  let cursor = 0;
  const placed = [];
  for (const child of list) {
    const dim = readDim(child, axis, fallback);
    placed.push({ child, offset: cursor, dim });
    cursor += dim + gap;
  }
  const total = Math.max(0, cursor - gap);
  return { placed, total };
}

function readDim(child, axis, fallback) {
  if (!child || typeof child !== "object" || !child.props) return fallback;
  const { props } = child;
  if (axis === "y") {
    if (typeof props.height === "number") return props.height;
    if (typeof props.h === "number") return props.h;
  } else {
    if (typeof props.width === "number") return props.width;
    if (typeof props.w === "number") return props.w;
  }
  // Heuristics for built-in primitives without explicit size:
  //   Text/H1/H2/H3 — derived from typography scale.
  //   everything else — `fallback`.
  return fallback;
}

/**
 * Wrap fragment in a translate group.
 */
export function translate(x, y, body) {
  return React.createElement("g", { transform: `translate(${x}, ${y})` }, body);
}

/**
 * Compute padding box dimensions for a card.
 */
export function paddedBox({ padding = 16, contentW, contentH }) {
  return { width: contentW + padding * 2, height: contentH + padding * 2 };
}
