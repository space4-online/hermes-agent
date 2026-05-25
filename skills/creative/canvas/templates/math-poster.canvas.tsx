/**
 * Math & Algorithm — academic conference poster style.
 *
 * Render:
 *   node ../scripts/render.mjs math-poster.canvas.tsx --width 1100 --height 1200
 *
 * This template intentionally uses a self-contained palette + serif typography
 * instead of useHostTheme(): academic posters carry a fixed visual identity
 * (navy ink, burgundy accent, mustard highlight, cream paper) that is
 * orthogonal to a host editor's light/dark theme.
 *
 * Topic on the poster: Binary Search — derivation of the Θ(log n) bound.
 * Replace the data block at the top of the file to retarget the same layout
 * to any other algorithm / theorem of similar shape.
 */

import React from "react";

// ---------- palette & typography ----------
const PAL = {
  ink:       "#1a2a4a",
  ink2:      "#3a527c",
  accent:    "#7d2d3a",
  highlight: "#c89b3c",
  paper:     "#fbf8f0",
  rule:      "#d8d2c2",
  muted:     "#5b5e6b",
  code:      "#102a43",
  codeBg:    "#f3eee0",
  formulaBg: "#ffffff",
  subtitle:  "#d6dbe3",
};
const SERIF = "Georgia, 'Times New Roman', 'Liberation Serif', serif";
const MONO  = "SFMono-Regular, Menlo, 'Courier New', monospace";

const W = 1100;
const H = 1200;

// ---------- content (swap this block to retarget the poster) ----------
const POSTER = {
  title:    "Binary Search",
  subtitle: "A logarithmic-time decision procedure for ordered arrays",
  series:   "HERMES CANVAS · ALGORITHMS 101",
  volume:   "poster series · vol. 1",
  abstract: [
    "We re-derive the worst-case running time of binary search by reducing each iteration to a halving of the",
    "candidate window, yielding the recurrence T(n) = T(n/2) + Θ(1) and the closed form Θ(log n).",
  ],
  problem: [
    "Given a sorted array A[0..n−1] of comparable",
    "elements and a target t, decide whether t ∈ A,",
    "and if so return any index i with A[i] = t.",
  ],
  invariantProse: [
    "If t ∈ A, then t ∈ A[lo..hi] at every iteration",
    "of the while-loop.",
  ],
  invariantFormula: "lo ≤ hi   ∧   t ∈ A  ⟹  t ∈ A[lo..hi]",
  pseudocode: [
    "function bsearch(A, t):",
    "    lo, hi ← 0, n − 1",
    "    while lo ≤ hi:",
    "        mid ← ⌊(lo + hi) / 2⌋",
    "        if   A[mid] = t : return mid",
    "        elif A[mid] < t : lo ← mid + 1",
    "        else           : hi ← mid − 1",
    "    return −1",
  ],
  recurrence:  "T(n) = T(n/2) + Θ(1)",
  closedForm:  "T(n) = Θ(log₂ n)",
  derivation: [
    "By the Master Theorem with a = 1, b = 2,",
    "f(n) = Θ(1), case 2 applies with k = 0, so",
    "T(n) ∈ Θ(log n).",
  ],
  table: {
    headers: ["n", "linear (steps)", "binary (steps)", "speedup"],
    rows: [
      ["10³",  "10³",  "≈ 10", "×100"],
      ["10⁶",  "10⁶",  "≈ 20", "×50,000"],
      ["10⁹",  "10⁹",  "≈ 30", "×33M"],
      ["10¹²", "10¹²", "≈ 40", "×25B"],
    ],
  },
  takeaways: [
    "Halving ⟹ ⌈log₂ n⌉ iterations worst-case.",
    "Sortedness is essential — unsorted ⟹ Θ(n).",
    "Stable variant: linear scan after first hit.",
    "Off-by-one bugs cluster at lo, hi, mid updates.",
  ],
  references: [
    "Knuth, TAOCP Vol. 3 §6.2.1",
    "CLRS 4th ed., Ch. 2",
    "Bentley, Programming Pearls Ch. 4",
  ],
};

// ---------- helpers ----------
function PageBg() {
  return (
    <g>
      <rect x={0} y={0} width={W} height={H} fill={PAL.paper} />
    </g>
  );
}

function TitleBand() {
  return (
    <g>
      <rect x={0} y={0} width={W} height={110} fill={PAL.ink} />
      <rect x={0} y={102} width={W} height={8} fill={PAL.highlight} />
      <text x={40} y={50} fontFamily={SERIF} fontSize={32} fontWeight={700} fill={PAL.paper}>
        {POSTER.title}
      </text>
      <text x={40} y={78} fontFamily={SERIF} fontSize={16} fontStyle="italic" fill={PAL.subtitle}>
        {POSTER.subtitle}
      </text>
      <text x={W - 40} y={50} textAnchor="end" fontFamily={SERIF} fontSize={13}
        fill={PAL.highlight} letterSpacing="0.12em">
        {POSTER.series}
      </text>
      <text x={W - 40} y={72} textAnchor="end" fontFamily={SERIF} fontSize={12}
        fontStyle="italic" fill={PAL.subtitle}>
        {POSTER.volume}
      </text>
    </g>
  );
}

function Abstract({ y }: { y: number }) {
  return (
    <g transform={`translate(40, ${y})`}>
      <rect x={0} y={0} width={W - 80} height={64} fill="#ffffff" stroke={PAL.rule} />
      <rect x={0} y={0} width={4} height={64} fill={PAL.accent} />
      <text x={20} y={20} fontFamily={SERIF} fontSize={11} letterSpacing="0.2em"
        fontWeight={700} fill={PAL.accent}>ABSTRACT</text>
      {POSTER.abstract.map((ln, i) => (
        <text key={i} x={20} y={40 + i * 16} fontFamily={SERIF} fontSize={13} fill={PAL.ink}>
          {ln}
        </text>
      ))}
    </g>
  );
}

function Section(props: { title: string; x: number; y: number; width: number; children: React.ReactNode }) {
  return (
    <g transform={`translate(${props.x}, ${props.y})`}>
      <line x1={0} y1={0} x2={props.width} y2={0} stroke={PAL.ink} strokeWidth={2} />
      <text x={0} y={22} fontFamily={SERIF} fontSize={11} letterSpacing="0.2em"
        fontWeight={700} fill={PAL.accent}>{String(props.title).toUpperCase()}</text>
      <g transform="translate(0, 38)">{props.children}</g>
    </g>
  );
}

function Body({ lines, italic = false, lh = 18, fs = 13 }: { lines: string[]; italic?: boolean; lh?: number; fs?: number }) {
  return (
    <g>
      {lines.map((ln, i) => (
        <text key={i} x={0} y={i * lh} fontFamily={SERIF} fontSize={fs}
          fontStyle={italic ? "italic" : "normal"} fill={PAL.ink}>{ln}</text>
      ))}
    </g>
  );
}

function CodeBlock({ lines, width }: { lines: string[]; width: number }) {
  const h_ = lines.length * 18 + 20;
  return (
    <g>
      <rect x={0} y={0} width={width} height={h_} fill={PAL.codeBg} stroke={PAL.rule} />
      {lines.map((ln, i) => (
        <text key={i} x={14} y={20 + i * 18} fontFamily={MONO} fontSize={12} fill={PAL.code}>{ln}</text>
      ))}
    </g>
  );
}

function Formula({ text, big = false, width = 460 }: { text: string; big?: boolean; width?: number }) {
  const fs = big ? 22 : 16;
  const h_ = big ? 60 : 38;
  return (
    <g>
      <rect x={0} y={0} width={width} height={h_} fill={PAL.formulaBg} stroke={PAL.rule} />
      <text x={width / 2} y={big ? 38 : 24} textAnchor="middle"
        fontFamily={SERIF} fontSize={fs} fontStyle="italic" fill={PAL.ink}>{text}</text>
    </g>
  );
}

function ShrinkingWindow() {
  const totalW = 460;
  const rowH = 26;
  const gap = 10;
  const palette = [PAL.ink, PAL.ink2, "#7088b0", PAL.highlight];
  const widths = [totalW, totalW / 2, totalW / 4, totalW / 8];
  const labels = ["n", "n/2", "n/4", "n/8"];
  return (
    <g>
      {widths.map((w, i) => (
        <g key={i} transform={`translate(0, ${i * (rowH + gap)})`}>
          <rect x={0} y={0} width={totalW} height={rowH} fill={PAL.codeBg} stroke={PAL.rule} />
          <rect x={0} y={0} width={w} height={rowH} fill={palette[i]} />
          <text x={w / 2} y={17} textAnchor="middle" fontFamily={SERIF} fontStyle="italic" fontSize={12} fill="#fff">
            {labels[i]}
          </text>
          <text x={totalW + 10} y={17} fontFamily={SERIF} fontSize={11} fill={PAL.muted}>
            iter {i + 1}
          </text>
        </g>
      ))}
    </g>
  );
}

function ComparisonTable() {
  const cols = [80, 200, 200, 140];
  const xs = [0];
  for (let i = 0; i < cols.length; i++) xs.push(xs[i] + cols[i]);
  const totalW = xs[xs.length - 1]; // 620
  const headH = 28;
  const rowH = 26;
  const totalH = headH + POSTER.table.rows.length * rowH;
  return (
    <g>
      <rect x={0} y={0} width={totalW} height={totalH} fill="#fff" stroke={PAL.ink} strokeWidth={1.5} />
      <rect x={0} y={0} width={totalW} height={headH} fill={PAL.ink} />
      {POSTER.table.headers.map((h, i) => (
        <text key={i} x={xs[i] + 12} y={18} fontFamily={SERIF} fontSize={12} fontWeight={700} fill={PAL.paper}>{h}</text>
      ))}
      {POSTER.table.rows.map((row, ri) => (
        <g key={ri}>
          {ri % 2 === 1 ? (
            <rect x={0} y={headH + ri * rowH} width={totalW} height={rowH} fill={PAL.codeBg} />
          ) : null}
          {row.map((cell, ci) => (
            <text key={ci} x={xs[ci] + 12} y={headH + ri * rowH + 17}
              fontFamily={ci === 0 || ci === 3 ? SERIF : MONO} fontSize={12} fill={PAL.ink}
              fontStyle={ci === 0 ? "italic" : "normal"}>{cell}</text>
          ))}
        </g>
      ))}
      {xs.slice(1, -1).map((cx, i) => (
        <line key={i} x1={cx} y1={headH} x2={cx} y2={totalH} stroke={PAL.rule} />
      ))}
    </g>
  );
}

function Takeaways({ items, width = 380 }: { items: string[]; width?: number }) {
  const lineH = 22;
  const padding = 16;
  const totalH = padding * 2 + items.length * lineH + 8;
  return (
    <g>
      <rect x={0} y={0} width={width} height={totalH} fill="#fff" stroke={PAL.accent} strokeWidth={1.5} />
      <rect x={0} y={0} width={4} height={totalH} fill={PAL.accent} />
      <text x={padding} y={padding + 10} fontFamily={SERIF} fontSize={11} letterSpacing="0.2em"
        fontWeight={700} fill={PAL.accent}>KEY TAKEAWAYS</text>
      {items.map((it, i) => (
        <g key={i} transform={`translate(${padding}, ${padding + 28 + i * lineH})`}>
          <circle cx={5} cy={6} r={3} fill={PAL.highlight} />
          <text x={16} y={10} fontFamily={SERIF} fontSize={13} fill={PAL.ink}>{it}</text>
        </g>
      ))}
    </g>
  );
}

function Footer({ items }: { items: string[] }) {
  return (
    <g>
      <rect x={0} y={0} width={W} height={50} fill={PAL.ink} />
      <text x={40} y={20} fontFamily={SERIF} fontSize={11} letterSpacing="0.2em"
        fontWeight={700} fill={PAL.highlight}>REFERENCES</text>
      {items.map((it, i) => (
        <text key={i} x={40 + i * 340} y={40} fontFamily={SERIF} fontSize={11}
          fill={PAL.paper} fontStyle="italic">[{i + 1}] {it}</text>
      ))}
    </g>
  );
}

// ---------- top-level layout ----------
export default function MathAlgorithmPoster() {
  const yAbstract = 130;
  const yBody     = 220;
  const yBottom   = 790;
  const yTakeaway = 980;
  const yFooter   = 1140;

  const left  = 40;
  const right = W / 2 + 20; // 570
  const colW  = (W - 80) / 2 - 20; // 490

  return (
    <g>
      <PageBg />
      <TitleBand />
      <Abstract y={yAbstract} />

      {/* Left column */}
      <Section title="Problem" x={left} y={yBody} width={colW}>
        <Body lines={POSTER.problem} />
      </Section>

      <Section title="Loop Invariant" x={left} y={yBody + 130} width={colW}>
        <Body italic lines={POSTER.invariantProse} />
        <g transform="translate(0, 50)">
          <Formula text={POSTER.invariantFormula} width={colW - 30} />
        </g>
      </Section>

      <Section title="Figure: Window Halving" x={left} y={yBody + 290} width={colW}>
        <ShrinkingWindow />
        <text x={0} y={160} fontFamily={SERIF} fontStyle="italic" fontSize={11} fill={PAL.muted}>
          Each iteration discards half of the candidate window.
        </text>
      </Section>

      {/* Right column */}
      <Section title="Algorithm" x={right} y={yBody} width={colW}>
        <CodeBlock lines={POSTER.pseudocode} width={colW} />
      </Section>

      <Section title="Recurrence & Closed Form" x={right} y={yBody + 230} width={colW}>
        <Formula text={POSTER.recurrence} width={colW - 30} />
        <g transform="translate(0, 56)">
          <Formula text={POSTER.closedForm} big width={colW - 30} />
        </g>
        <g transform="translate(0, 134)">
          <Body lines={POSTER.derivation} />
        </g>
      </Section>

      {/* Bottom: comparison table full width */}
      <Section title="Empirical Step Counts" x={left} y={yBottom} width={W - 80}>
        <ComparisonTable />
      </Section>

      {/* Takeaways block, right aligned */}
      <g transform={`translate(${W - 40 - 380}, ${yTakeaway})`}>
        <Takeaways items={POSTER.takeaways} width={380} />
      </g>

      <g transform={`translate(0, ${yFooter})`}>
        <Footer items={POSTER.references} />
      </g>
    </g>
  );
}
