/**
 * math-figure.canvas.tsx
 * --------------------------------------------------------------------------
 * Single-figure scale, paper-style illustration of a math / algorithm idea.
 * Default subject: a multilayer perceptron (MLP) architecture diagram.
 *
 * Design intent: this is NOT a poster. It is the kind of figure you would
 * embed in a paper or technical note — restrained palette, rule line above
 * the caption, "Figure N. Title. Description." block underneath.
 *
 * To re-purpose for another figure (e.g. a state machine, data structure,
 * or geometric diagram), keep <Caption /> + page background and replace
 * <NetworkGraph /> with your own <g>...</g> body. The FIGURE constant is
 * the only place you should need to edit for an MLP variant.
 */

import React from "react";

// -- visual identity ---------------------------------------------------------
const PAL = {
  ink:        "#1a1a1a",
  bg:         "#ffffff",
  nodeFill:   "#ffffff",
  nodeStroke: "#1a1a1a",
  edge:       "#cfd2d6",
  accent:     "#1a4f9c",
  accentSoft: "#e9eef9",
  caption:    "#333333",
  muted:      "#6a6f78",
  rule:       "#bfc3c9",
};

const SERIF = "Georgia, 'Times New Roman', 'Liberation Serif', serif";
const SANS  = "'Helvetica Neue', Arial, 'Liberation Sans', sans-serif";

// -- canvas geometry ---------------------------------------------------------
const W = 720;
const H = 460;

const LEFT  = 60;
const RIGHT = 60;
const NETW  = W - LEFT - RIGHT; // 600

const BAND_TOP    = 100;
const BAND_BOTTOM = 320;
const BAND_CENTER = (BAND_TOP + BAND_BOTTOM) / 2;

const NODE_R = 14;
const VGAP   = 36;

// -- subject content ---------------------------------------------------------
type Layer = { name: string; size: number; dim: string; accent?: boolean };

const FIGURE: {
  number: string;
  title: string;
  caption: string[];
  layers: Layer[];
} = {
  number: "Figure 1",
  title:  "Multilayer perceptron with two hidden layers",
  caption: [
    "Fully-connected feed-forward network with ReLU activations on the hidden layers and a softmax",
    "head over three classes. Edges depict the weight matrices W₁ ∈ ℝ⁶ˣ⁴, W₂ ∈ ℝ⁶ˣ⁶, W₃ ∈ ℝ³ˣ⁶;",
    "biases are folded into the weights for clarity. The shaded layer is the prediction head.",
  ],
  layers: [
    { name: "input",    size: 4, dim: "x ∈ ℝ⁴" },
    { name: "hidden 1", size: 6, dim: "h₁ = ReLU(W₁x)" },
    { name: "hidden 2", size: 6, dim: "h₂ = ReLU(W₂h₁)" },
    { name: "output",   size: 3, dim: "ŷ = softmax(W₃h₂)", accent: true },
  ],
};

// -- helpers -----------------------------------------------------------------
function subscript(n: number): string {
  const map = ["₀","₁","₂","₃","₄","₅","₆","₇","₈","₉"];
  return String(n).split("").map(c => map[Number(c)] ?? c).join("");
}

type Pos = { x: number; y: number };

function layerPositions(): Pos[][] {
  const L = FIGURE.layers.length;
  const stepX = NETW / (L - 1);
  return FIGURE.layers.map((layer, i) => {
    const x = LEFT + i * stepX;
    const totalH = (layer.size - 1) * VGAP;
    const startY = BAND_CENTER - totalH / 2;
    return Array.from({ length: layer.size }, (_, k) => ({
      x,
      y: startY + k * VGAP,
    }));
  });
}

// -- pieces ------------------------------------------------------------------
function NetworkGraph() {
  const layers = layerPositions();

  const edges: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (let i = 0; i < layers.length - 1; i++) {
    for (const a of layers[i]) {
      for (const b of layers[i + 1]) {
        edges.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
      }
    }
  }

  return (
    <g>
      {/* weight-matrix labels above the gaps */}
      {layers.slice(0, -1).map((nodes, li) => {
        const cx = (nodes[0].x + layers[li + 1][0].x) / 2;
        return (
          <text
            key={`w-${li}`}
            x={cx}
            y={BAND_TOP - 10}
            textAnchor="middle"
            fontFamily={SERIF}
            fontSize={13}
            fontStyle="italic"
            fill={PAL.ink}
          >
            {`W${subscript(li + 1)}`}
          </text>
        );
      })}

      {/* edges drawn first so nodes overlay them */}
      {edges.map((e, i) => (
        <line
          key={`e-${i}`}
          x1={e.x1}
          y1={e.y1}
          x2={e.x2}
          y2={e.y2}
          stroke={PAL.edge}
          strokeWidth={0.7}
        />
      ))}

      {/* nodes */}
      {layers.map((nodes, li) => {
        const isAccent = !!FIGURE.layers[li].accent;
        return nodes.map((n, ni) => (
          <circle
            key={`n-${li}-${ni}`}
            cx={n.x}
            cy={n.y}
            r={NODE_R}
            fill={isAccent ? PAL.accentSoft : PAL.nodeFill}
            stroke={isAccent ? PAL.accent : PAL.nodeStroke}
            strokeWidth={1.4}
          />
        ));
      })}

      {/* layer labels under nodes */}
      {layers.map((nodes, li) => {
        const x = nodes[0].x;
        const layer = FIGURE.layers[li];
        return (
          <g key={`lbl-${li}`} transform={`translate(${x}, ${BAND_BOTTOM + 28})`}>
            <text
              x={0}
              y={0}
              textAnchor="middle"
              fontFamily={SANS}
              fontSize={12}
              fontWeight={700}
              fill={layer.accent ? PAL.accent : PAL.ink}
            >
              {layer.name}
            </text>
            <text
              x={0}
              y={18}
              textAnchor="middle"
              fontFamily={SERIF}
              fontSize={11}
              fontStyle="italic"
              fill={PAL.muted}
            >
              {layer.dim}
            </text>
            <text
              x={0}
              y={34}
              textAnchor="middle"
              fontFamily={SANS}
              fontSize={10}
              fill={PAL.muted}
            >
              {`d = ${layer.size}`}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function Caption() {
  const x = LEFT;
  const y = H - 70;
  const numberWidth = 56;

  return (
    <g transform={`translate(${x}, ${y})`}>
      <line
        x1={0}
        y1={-14}
        x2={W - LEFT - RIGHT}
        y2={-14}
        stroke={PAL.rule}
        strokeWidth={0.8}
      />
      <text
        x={0}
        y={6}
        fontFamily={SERIF}
        fontSize={12}
        fontWeight={700}
        fill={PAL.ink}
      >
        {`${FIGURE.number}.`}
      </text>
      <text
        x={numberWidth}
        y={6}
        fontFamily={SERIF}
        fontSize={12}
        fontStyle="italic"
        fill={PAL.ink}
      >
        {`${FIGURE.title}.`}
      </text>
      {FIGURE.caption.map((ln, i) => (
        <text
          key={i}
          x={0}
          y={26 + i * 15}
          fontFamily={SERIF}
          fontSize={11}
          fill={PAL.caption}
        >
          {ln}
        </text>
      ))}
    </g>
  );
}

// -- root --------------------------------------------------------------------
export default function MathFigure() {
  return (
    <g>
      <rect x={0} y={0} width={W} height={H} fill={PAL.bg} />
      <NetworkGraph />
      <Caption />
    </g>
  );
}
