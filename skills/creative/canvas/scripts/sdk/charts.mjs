// Charts — minimal SVG implementations for BarChart, LineChart, PieChart.
// No external chart lib. Each component computes its own paths so the
// resulting SVG is fully self-contained.

import React from "react";
import { useHostTheme } from "./hooks.mjs";

const h = React.createElement;

const FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";

function tonePalette(tokens, tone, fallback) {
  const lookup = {
    info:    tokens.status.info,
    success: tokens.status.success,
    warning: tokens.status.warning,
    danger:  tokens.status.danger,
    accent:  tokens.accent.control,
    neutral: tokens.text.tertiary,
  };
  return lookup[tone] || fallback;
}

function pickColor(seriesColor, tokens, idx) {
  if (seriesColor) return seriesColor;
  return tokens.chart.sequence[idx % tokens.chart.sequence.length];
}

export function BarChart({ data = [], series, width = 480, height = 240, x = 0, y = 0, tone = "info", title }) {
  const { tokens } = useHostTheme();
  const padL = 44, padR = 12, padT = title ? 32 : 16, padB = 28;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const points = data.map(d => ({ label: d.label, value: Number(d.value) || 0 }));
  const maxV = Math.max(1, ...points.map(p => p.value));
  const barColor = pickColor(series && series.color, tokens, 0) || tonePalette(tokens, tone, tokens.accent.control);
  const barW = points.length ? chartW / points.length * 0.6 : 0;
  const slotW = points.length ? chartW / points.length : 0;

  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: tokens.radius.md, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    title ? h("text", { x: padL, y: 22, fontSize: 13, fontWeight: 600, fill: tokens.text.primary, fontFamily: FONT }, title) : null,
    // y axis baseline
    h("line", { x1: padL, y1: padT + chartH, x2: padL + chartW, y2: padT + chartH, stroke: tokens.stroke.tertiary }),
    // gridlines
    [0.25, 0.5, 0.75, 1].map((r, i) =>
      h("line", { key: `g${i}`, x1: padL, y1: padT + chartH * (1 - r), x2: padL + chartW, y2: padT + chartH * (1 - r),
        stroke: tokens.stroke.quaternary, strokeDasharray: "2 4" })
    ),
    // bars + labels
    points.map((p, i) => {
      const bh = (p.value / maxV) * chartH;
      const bx = padL + i * slotW + (slotW - barW) / 2;
      return h(React.Fragment, { key: i },
        h("rect", { x: bx, y: padT + chartH - bh, width: barW, height: bh, rx: 2, fill: barColor }),
        h("text", { x: bx + barW / 2, y: padT + chartH + 16, fontSize: 11, textAnchor: "middle",
          fill: tokens.text.tertiary, fontFamily: FONT }, p.label),
      );
    }),
    // y labels (min/max)
    h("text", { x: padL - 6, y: padT + chartH + 4, fontSize: 11, textAnchor: "end", fill: tokens.text.tertiary, fontFamily: FONT }, "0"),
    h("text", { x: padL - 6, y: padT + 4,            fontSize: 11, textAnchor: "end", fill: tokens.text.tertiary, fontFamily: FONT }, String(maxV)),
  );
}

export function LineChart({ series = [], width = 480, height = 240, x = 0, y = 0, title, xLabels = [] }) {
  const { tokens } = useHostTheme();
  const padL = 44, padR = 12, padT = title ? 32 : 16, padB = 28;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const allValues = series.flatMap(s => s.data.map(d => Number(d.value) || 0));
  const maxV = Math.max(1, ...allValues);
  const minV = Math.min(0, ...allValues);
  const range = Math.max(1, maxV - minV);
  const labels = xLabels.length ? xLabels : (series[0] && series[0].data.map(d => d.label)) || [];
  const stepX = labels.length > 1 ? chartW / (labels.length - 1) : 0;

  function path(s) {
    return s.data
      .map((d, i) => {
        const px = padL + i * stepX;
        const py = padT + chartH - ((Number(d.value) - minV) / range) * chartH;
        return `${i === 0 ? "M" : "L"} ${px.toFixed(1)} ${py.toFixed(1)}`;
      })
      .join(" ");
  }

  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: tokens.radius.md, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    title ? h("text", { x: padL, y: 22, fontSize: 13, fontWeight: 600, fill: tokens.text.primary, fontFamily: FONT }, title) : null,
    h("line", { x1: padL, y1: padT + chartH, x2: padL + chartW, y2: padT + chartH, stroke: tokens.stroke.tertiary }),
    [0.25, 0.5, 0.75, 1].map((r, i) =>
      h("line", { key: `g${i}`, x1: padL, y1: padT + chartH * (1 - r), x2: padL + chartW, y2: padT + chartH * (1 - r),
        stroke: tokens.stroke.quaternary, strokeDasharray: "2 4" })
    ),
    series.map((s, idx) =>
      h("path", { key: idx, d: path(s), fill: "none",
        stroke: pickColor(s.color, tokens, idx), strokeWidth: 1.6, strokeLinejoin: "round", strokeLinecap: "round" })
    ),
    labels.map((lbl, i) =>
      h("text", { key: `xl${i}`, x: padL + i * stepX, y: padT + chartH + 18, fontSize: 11, textAnchor: "middle",
        fill: tokens.text.tertiary, fontFamily: FONT }, lbl)
    ),
    h("text", { x: padL - 6, y: padT + chartH + 4, fontSize: 11, textAnchor: "end", fill: tokens.text.tertiary, fontFamily: FONT }, String(minV)),
    h("text", { x: padL - 6, y: padT + 4,            fontSize: 11, textAnchor: "end", fill: tokens.text.tertiary, fontFamily: FONT }, String(maxV)),
  );
}

export function PieChart({ data = [], width = 280, height = 280, x = 0, y = 0, title, donut = true }) {
  const { tokens } = useHostTheme();
  const padT = title ? 32 : 16;
  const radius = Math.min(width, height - padT) / 2 - 12;
  const cx = width / 2;
  const cy = padT + (height - padT) / 2;

  const total = data.reduce((s, d) => s + (Number(d.value) || 0), 0) || 1;
  let acc = 0;
  const slices = data.map((d, i) => {
    const v = Number(d.value) || 0;
    const start = (acc / total) * Math.PI * 2 - Math.PI / 2;
    acc += v;
    const end = (acc / total) * Math.PI * 2 - Math.PI / 2;
    const large = end - start > Math.PI ? 1 : 0;
    const x1 = cx + radius * Math.cos(start);
    const y1 = cy + radius * Math.sin(start);
    const x2 = cx + radius * Math.cos(end);
    const y2 = cy + radius * Math.sin(end);
    const path = `M ${cx} ${cy} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${radius} ${radius} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`;
    return { path, color: pickColor(d.color, tokens, i), label: d.label, value: v };
  });

  return h("g", { transform: `translate(${x}, ${y})`, "data-w": width, "data-h": height },
    h("rect", { x: 0, y: 0, width, height, rx: tokens.radius.md, fill: tokens.bg.elevated, stroke: tokens.stroke.tertiary }),
    title ? h("text", { x: 14, y: 22, fontSize: 13, fontWeight: 600, fill: tokens.text.primary, fontFamily: FONT }, title) : null,
    slices.map((s, i) => h("path", { key: i, d: s.path, fill: s.color, stroke: tokens.bg.elevated, strokeWidth: 1 })),
    donut ? h("circle", { cx, cy, r: radius * 0.55, fill: tokens.bg.elevated }) : null,
  );
}
