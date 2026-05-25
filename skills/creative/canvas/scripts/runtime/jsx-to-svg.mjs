// JSX element tree -> SVG string.
// We do NOT pull in react-dom; instead we walk React elements directly:
//   - function component  -> invoke and recurse on its return value
//   - Fragment / array    -> recurse on children
//   - string tag (svg/g/rect/text/path/...) -> emit "<tag attrs>...</tag>"
//   - primitives (string / number) -> emit escaped text
// React hooks are NOT supported on this walker. Provide noop-style helpers
// (see sdk/hooks.mjs) instead of useState/useEffect inside .canvas.tsx files.

import React from "react";

const FRAGMENT = React.Fragment;

// SVG attributes that must be preserved in camelCase (otherwise auto-kebab).
const KEEP_CAMEL = new Set([
  "viewBox", "preserveAspectRatio",
  "gradientUnits", "gradientTransform",
  "patternUnits", "patternTransform", "patternContentUnits",
  "markerWidth", "markerHeight", "markerUnits", "refX", "refY",
  "spreadMethod", "maskUnits", "maskContentUnits",
  "lengthAdjust", "textLength",
  "baseFrequency", "numOctaves",
  "kernelMatrix", "kernelUnitLength",
  "surfaceScale", "specularConstant", "specularExponent",
  "lightingColor",
  "primitiveUnits", "filterUnits", "filterRes",
  "stdDeviation", "in", "in2", "result", "operator",
  "tableValues", "slope", "intercept", "amplitude",
  "exponent", "offset",
  "calcMode", "keyTimes", "keySplines",
  "attributeName", "attributeType", "begin", "dur", "end",
  "repeatCount", "repeatDur", "fill",
]);

// Self-closing void-style SVG elements (no children content emitted).
const VOID_TAGS = new Set([
  "circle", "ellipse", "line", "path", "polygon", "polyline", "rect",
  "stop", "use", "image", "feFlood", "feMergeNode",
  "feColorMatrix", "feGaussianBlur", "feOffset", "feBlend", "feComposite",
]);

// Tags that may legitimately have children rendered as inline content.
// Anything not in VOID_TAGS goes through open/close form.

function escape(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function camelToKebab(name) {
  if (KEEP_CAMEL.has(name)) return name;
  if (name === "className") return "class";
  if (name === "htmlFor") return "for";
  if (name === "xlinkHref") return "xlink:href";
  if (name === "xmlnsXlink") return "xmlns:xlink";
  return name.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
}

function styleToCss(style) {
  if (!style || typeof style !== "object") return "";
  const parts = [];
  for (const [k, v] of Object.entries(style)) {
    if (v == null || v === false) continue;
    const key = k.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
    const val = typeof v === "number" && !UNITLESS.has(k) ? `${v}px` : v;
    parts.push(`${key}: ${val}`);
  }
  return parts.join("; ");
}

const UNITLESS = new Set([
  "opacity", "zIndex", "fontWeight", "lineHeight", "flex", "order",
  "fillOpacity", "strokeOpacity", "strokeMiterlimit", "strokeDashoffset",
]);

function serializeAttrs(props) {
  if (!props) return "";
  const out = [];
  for (const [name, raw] of Object.entries(props)) {
    if (name === "children" || name === "key" || name === "ref") continue;
    if (raw == null || raw === false) continue;
    if (typeof raw === "function") continue;

    if (name === "style") {
      const css = styleToCss(raw);
      if (css) out.push(`style="${escape(css)}"`);
      continue;
    }
    if (raw === true) {
      out.push(camelToKebab(name));
      continue;
    }
    out.push(`${camelToKebab(name)}="${escape(raw)}"`);
  }
  return out.length ? " " + out.join(" ") : "";
}

function flattenChildren(children) {
  if (children == null || children === false || children === true) return [];
  if (Array.isArray(children)) {
    const out = [];
    for (const c of children) out.push(...flattenChildren(c));
    return out;
  }
  return [children];
}

export function renderToSvgString(element) {
  return walk(element);
}

function walk(node) {
  if (node == null || node === false || node === true) return "";
  if (typeof node === "string") return escape(node);
  if (typeof node === "number" || typeof node === "bigint") return String(node);
  if (Array.isArray(node)) return node.map(walk).join("");

  if (!node || typeof node !== "object" || !("type" in node)) return "";

  const { type, props } = node;

  // Fragment
  if (type === FRAGMENT || type === Symbol.for("react.fragment")) {
    return flattenChildren(props && props.children).map(walk).join("");
  }

  // Function component
  if (typeof type === "function") {
    let result;
    try {
      result = type(props || {});
    } catch (err) {
      throw new Error(
        `Component ${type.displayName || type.name || "<anon>"} threw during render: ${err.message}`
      );
    }
    return walk(result);
  }

  // String tag: SVG element
  if (typeof type === "string") {
    const children = flattenChildren(props && props.children);
    const attrStr = serializeAttrs(props);
    if (VOID_TAGS.has(type) && children.length === 0) {
      return `<${type}${attrStr} />`;
    }
    const inner = children.map(walk).join("");
    return `<${type}${attrStr}>${inner}</${type}>`;
  }

  // Class components / unknown — best effort: try .render() if present
  if (type && typeof type === "object" && typeof type.render === "function") {
    return walk(type.render(props));
  }
  return "";
}

/**
 * Wrap arbitrary content in an outer <svg> if the root element is not already an svg.
 * @param {string} body - rendered svg fragment
 * @param {{width:number,height:number,bg?:string}} opts
 */
export function wrapAsSvgDocument(body, { width, height, bg }) {
  const trimmed = body.trim();
  if (trimmed.startsWith("<svg")) return trimmed;
  const bgRect = bg
    ? `<rect x="0" y="0" width="${width}" height="${height}" fill="${escape(bg)}" />`
    : "";
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" ` +
    `viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">` +
    bgRect + body +
    `</svg>`
  );
}
