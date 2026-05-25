/**
 * math-figure-transformer.canvas.tsx
 * --------------------------------------------------------------------------
 * Paper-figure-scale architecture diagram with a categorical color palette.
 * Subject: the original Transformer encoder–decoder (Vaswani et al., 2017).
 *
 * Compared to math-figure.canvas.tsx (intentionally monochrome), this
 * template demonstrates how to keep a "paper figure" feel while using
 * up to ~9 categorical fills to distinguish functional blocks
 * (embedding / positional / attention / norm / FFN / linear / softmax …).
 *
 * Each color comes from a desaturated, low-contrast pastel triad
 * (fill / stroke / text) so that every block reads as the same family
 * of "figure block", just hue-coded. This is the convention used by
 * many ML papers (Transformer, BERT, ViT, U-Net schematics).
 */

import React from "react";

// -- visual identity ---------------------------------------------------------
const PAL = {
  ink:        "#1a1a1a",
  bg:         "#fdfcf8",
  caption:    "#2e2e2e",
  rule:       "#c9c4b9",
  muted:      "#6a6f78",
  arrow:      "#3a4858",
};

type Cat = { fill: string; stroke: string; text: string };

const CAT: Record<string, Cat> = {
  embedding:  { fill: "#e8f3df", stroke: "#7c9b56", text: "#3d5828" },
  positional: { fill: "#ece4f3", stroke: "#7e64a3", text: "#3d2960" },
  attention:  { fill: "#dfeaf7", stroke: "#3d6fa8", text: "#1d3f6c" },
  maskedAttn: { fill: "#c9d8eb", stroke: "#2a4f80", text: "#15304f" },
  crossAttn:  { fill: "#d9ecea", stroke: "#3a8a82", text: "#1d4d49" },
  addNorm:    { fill: "#efebe4", stroke: "#a89e84", text: "#5b5345" },
  ffn:        { fill: "#f7e6d3", stroke: "#c2884b", text: "#6d4520" },
  linear:     { fill: "#e5e2dc", stroke: "#6e6960", text: "#33312d" },
  softmax:    { fill: "#f3deea", stroke: "#a64f87", text: "#5e1f47" },
};

const SERIF = "Georgia, 'Times New Roman', 'Liberation Serif', serif";
const SANS  = "'Helvetica Neue', Arial, 'Liberation Sans', sans-serif";

// -- canvas geometry ---------------------------------------------------------
const W = 760;
const H = 800;

const COL_W = 240;
const GAP   = 80;
const SIDE  = (W - 2 * COL_W - GAP) / 2;        // 100
const ENC_CX = SIDE + COL_W / 2;                // 220
const DEC_CX = SIDE + COL_W + GAP + COL_W / 2;  // 540

const BLOCK_H = 32;
const VGAP    = 12;
const ROW     = BLOCK_H + VGAP;                 // 44

// caption block reserved between main figure and watermark
const MAIN_FIG_BOTTOM = 620;                    // figure body ends here
const CAPTION_TOP = MAIN_FIG_BOTTOM - 90;       // 530
const LABEL_Y     = CAPTION_TOP - 30;           // 500  (Inputs / Outputs labels)
const Y0          = LABEL_Y - 30;               // 470  (first block center y)

// watermark band lives below the caption (this canvas occupies y = 620..800)
const WATERMARK_TOP    = MAIN_FIG_BOTTOM;       // 620 (dashed separator)
const WATERMARK_HEADER = WATERMARK_TOP + 16;    // 636 (small italic header)
const WM_BAND_TOP      = WATERMARK_TOP + 30;    // 650
const WM_BAND_H        = 140;
const WM_BAND_CENTER   = WM_BAND_TOP + WM_BAND_H / 2;  // 720
const WM_LAYERS        = [4, 6, 6, 3];
const WM_R             = 6;
const WM_VGAP          = 14;
const WM_W             = 600;
const WM_LEFT          = (W - WM_W) / 2;        // 80

const ENC_Y  = Array.from({ length: 6 }, (_, i) => Y0 - i * ROW);
const DEC_Y  = Array.from({ length: 8 }, (_, i) => Y0 - i * ROW);
const HEAD_Y = [DEC_Y[7] - ROW, DEC_Y[7] - 2 * ROW];
const OUT_PROB_Y = HEAD_Y[1] - BLOCK_H / 2 - 16;

// -- subject content ---------------------------------------------------------
type Block = { y: number; cat: Cat; label: string };

const ENC_BLOCKS: Block[] = [
  { y: ENC_Y[0], cat: CAT.embedding,  label: "Input Embedding" },
  { y: ENC_Y[1], cat: CAT.positional, label: "+ Positional Encoding" },
  { y: ENC_Y[2], cat: CAT.attention,  label: "Multi-Head Self-Attention" },
  { y: ENC_Y[3], cat: CAT.addNorm,    label: "Add & Norm" },
  { y: ENC_Y[4], cat: CAT.ffn,        label: "Feed-Forward" },
  { y: ENC_Y[5], cat: CAT.addNorm,    label: "Add & Norm" },
];

const DEC_BLOCKS: Block[] = [
  { y: DEC_Y[0], cat: CAT.embedding,  label: "Output Embedding" },
  { y: DEC_Y[1], cat: CAT.positional, label: "+ Positional Encoding" },
  { y: DEC_Y[2], cat: CAT.maskedAttn, label: "Masked Multi-Head Attention" },
  { y: DEC_Y[3], cat: CAT.addNorm,    label: "Add & Norm" },
  { y: DEC_Y[4], cat: CAT.crossAttn,  label: "Multi-Head Cross-Attention" },
  { y: DEC_Y[5], cat: CAT.addNorm,    label: "Add & Norm" },
  { y: DEC_Y[6], cat: CAT.ffn,        label: "Feed-Forward" },
  { y: DEC_Y[7], cat: CAT.addNorm,    label: "Add & Norm" },
];

const HEAD_BLOCKS: Block[] = [
  { y: HEAD_Y[0], cat: CAT.linear,  label: "Linear" },
  { y: HEAD_Y[1], cat: CAT.softmax, label: "Softmax" },
];

const FIGURE_TEXT = {
  number: "Figure 1",
  title:  "The Transformer encoder–decoder",
  caption: [
    "Both stacks are composed of N identical layers built from multi-head attention and",
    "position-wise feed-forward sub-layers, each wrapped in a residual connection followed",
    "by layer normalization. The decoder additionally attends over the encoder output via",
    "cross-attention (K, V from the encoder, Q from the previous decoder layer).",
  ],
};

// -- pieces ------------------------------------------------------------------
function FigureBlock(props: { cx: number; y: number; cat: Cat; label: string }) {
  const x = props.cx - COL_W / 2;
  const yT = props.y - BLOCK_H / 2;
  return (
    <g>
      <rect
        x={x}
        y={yT}
        width={COL_W}
        height={BLOCK_H}
        rx={6}
        ry={6}
        fill={props.cat.fill}
        stroke={props.cat.stroke}
        strokeWidth={1.2}
      />
      <text
        x={props.cx}
        y={props.y + 4}
        textAnchor="middle"
        fontFamily={SANS}
        fontSize={12}
        fontWeight={600}
        fill={props.cat.text}
      >
        {props.label}
      </text>
    </g>
  );
}

function VerticalArrow(props: { cx: number; fromY: number; toY: number }) {
  const start = props.fromY - BLOCK_H / 2;
  const end   = props.toY + BLOCK_H / 2 + 6;
  return (
    <line
      x1={props.cx}
      y1={start}
      x2={props.cx}
      y2={end}
      stroke={PAL.arrow}
      strokeWidth={1.4}
      markerEnd="url(#arrow)"
    />
  );
}

function LabelToFirstBlock(props: { cx: number; labelY: number; blockY: number }) {
  return (
    <line
      x1={props.cx}
      y1={props.labelY - 10}
      x2={props.cx}
      y2={props.blockY + BLOCK_H / 2 + 6}
      stroke={PAL.arrow}
      strokeWidth={1.4}
      markerEnd="url(#arrow)"
    />
  );
}

function CrossAttentionArrow() {
  // Encoder top Add&Norm at (ENC_CX, ENC_Y[5]); Decoder Cross-Attn at (DEC_CX, DEC_Y[4]).
  // Encoder top is HIGHER (smaller y) than decoder cross-attn, so route up-then-right-then-down-then-in.
  const fromX = ENC_CX + COL_W / 2;
  const fromY = ENC_Y[5];
  const toX   = DEC_CX - COL_W / 2 - 6;
  const toY   = DEC_Y[4];
  const midX  = (fromX + toX) / 2;
  const path  = `M ${fromX} ${fromY} L ${midX} ${fromY} L ${midX} ${toY} L ${toX} ${toY}`;
  return (
    <g>
      <path
        d={path}
        fill="none"
        stroke={PAL.arrow}
        strokeWidth={1.4}
        markerEnd="url(#arrow)"
      />
      <text
        x={midX + 6}
        y={(fromY + toY) / 2 - 4}
        fontFamily={SERIF}
        fontStyle="italic"
        fontSize={11}
        fill={PAL.arrow}
      >
        K, V
      </text>
    </g>
  );
}

function NxBadge(props: { x: number; y: number; anchor: "start" | "end" }) {
  return (
    <text
      x={props.x}
      y={props.y}
      textAnchor={props.anchor}
      fontFamily={SERIF}
      fontStyle="italic"
      fontSize={14}
      fill={PAL.muted}
    >
      N×
    </text>
  );
}

// -- watermark --------------------------------------------------------------
// Faded MLP (the math-figure default subject) embedded as a watermark below
// the caption. The watermark is the visual signature of the prior figure;
// labels and caption are intentionally omitted so it reads as a mark, not a
// second figure.
function mlpWMPositions() {
  const stepX = WM_W / (WM_LAYERS.length - 1);
  return WM_LAYERS.map((size, i) => {
    const x = WM_LEFT + i * stepX;
    const totalH = (size - 1) * WM_VGAP;
    const startY = WM_BAND_CENTER - totalH / 2;
    return Array.from({ length: size }, (_, k) => ({
      x,
      y: startY + k * WM_VGAP,
    }));
  });
}

function MlpWatermark() {
  const layers = mlpWMPositions();
  const edges: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (let i = 0; i < layers.length - 1; i++) {
    for (const a of layers[i]) {
      for (const b of layers[i + 1]) {
        edges.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
      }
    }
  }

  return (
    <g opacity={0.18}>
      {edges.map((e, i) => (
        <line
          key={`we-${i}`}
          x1={e.x1}
          y1={e.y1}
          x2={e.x2}
          y2={e.y2}
          stroke="#1a1a1a"
          strokeWidth={0.5}
        />
      ))}
      {layers.map((nodes, li) => {
        const isOutput = li === layers.length - 1;
        return nodes.map((n, ni) => (
          <circle
            key={`wn-${li}-${ni}`}
            cx={n.x}
            cy={n.y}
            r={WM_R}
            fill={isOutput ? "#e9eef9" : "#ffffff"}
            stroke={isOutput ? "#1a4f9c" : "#1a1a1a"}
            strokeWidth={0.8}
          />
        ));
      })}
    </g>
  );
}

function WatermarkBand() {
  return (
    <g>
      <line
        x1={SIDE}
        y1={WATERMARK_TOP}
        x2={W - SIDE}
        y2={WATERMARK_TOP}
        stroke={PAL.rule}
        strokeWidth={0.6}
        strokeDasharray="4 4"
      />
      <text
        x={SIDE}
        y={WATERMARK_HEADER}
        fontFamily={SERIF}
        fontStyle="italic"
        fontSize={10}
        fill={PAL.muted}
      >
        Watermark · prior figure (multilayer perceptron)
      </text>
      <MlpWatermark />
    </g>
  );
}

function Caption() {
  return (
    <g transform={`translate(${SIDE}, ${CAPTION_TOP})`}>
      <line
        x1={0}
        y1={0}
        x2={W - 2 * SIDE}
        y2={0}
        stroke={PAL.rule}
        strokeWidth={0.8}
      />
      <text
        x={0}
        y={18}
        fontFamily={SERIF}
        fontSize={12}
        fontWeight={700}
        fill={PAL.ink}
      >
        {`${FIGURE_TEXT.number}.`}
      </text>
      <text
        x={56}
        y={18}
        fontFamily={SERIF}
        fontSize={12}
        fontStyle="italic"
        fill={PAL.ink}
      >
        {`${FIGURE_TEXT.title}.`}
      </text>
      {FIGURE_TEXT.caption.map((ln, i) => (
        <text
          key={i}
          x={0}
          y={36 + i * 14}
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
export default function MathFigureTransformer() {
  return (
    <g>
      <rect x={0} y={0} width={W} height={H} fill={PAL.bg} />

      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill={PAL.arrow} />
        </marker>
      </defs>

      {/* Encoder column */}
      <text
        x={ENC_CX}
        y={LABEL_Y + 5}
        textAnchor="middle"
        fontFamily={SERIF}
        fontStyle="italic"
        fontSize={12}
        fill={PAL.muted}
      >
        Inputs
      </text>
      <LabelToFirstBlock cx={ENC_CX} labelY={LABEL_Y} blockY={ENC_Y[0]} />
      {ENC_BLOCKS.map((b, i) => (
        <FigureBlock key={`e-${i}`} cx={ENC_CX} y={b.y} cat={b.cat} label={b.label} />
      ))}
      {ENC_BLOCKS.slice(1).map((b, i) => (
        <VerticalArrow key={`ea-${i}`} cx={ENC_CX} fromY={ENC_BLOCKS[i].y} toY={b.y} />
      ))}
      <NxBadge
        x={SIDE - 10}
        y={(ENC_Y[2] + ENC_Y[5]) / 2 + 4}
        anchor="end"
      />

      {/* Decoder column */}
      <text
        x={DEC_CX}
        y={LABEL_Y + 5}
        textAnchor="middle"
        fontFamily={SERIF}
        fontStyle="italic"
        fontSize={12}
        fill={PAL.muted}
      >
        Outputs (shifted right)
      </text>
      <LabelToFirstBlock cx={DEC_CX} labelY={LABEL_Y} blockY={DEC_Y[0]} />
      {DEC_BLOCKS.map((b, i) => (
        <FigureBlock key={`d-${i}`} cx={DEC_CX} y={b.y} cat={b.cat} label={b.label} />
      ))}
      {DEC_BLOCKS.slice(1).map((b, i) => (
        <VerticalArrow key={`da-${i}`} cx={DEC_CX} fromY={DEC_BLOCKS[i].y} toY={b.y} />
      ))}
      <NxBadge
        x={DEC_CX + COL_W / 2 + 12}
        y={(DEC_Y[2] + DEC_Y[7]) / 2 + 4}
        anchor="start"
      />

      {/* Output head: Linear → Softmax → Output Probabilities */}
      <VerticalArrow cx={DEC_CX} fromY={DEC_Y[7]} toY={HEAD_Y[0]} />
      {HEAD_BLOCKS.map((b, i) => (
        <FigureBlock key={`h-${i}`} cx={DEC_CX} y={b.y} cat={b.cat} label={b.label} />
      ))}
      <VerticalArrow cx={DEC_CX} fromY={HEAD_Y[0]} toY={HEAD_Y[1]} />
      <line
        x1={DEC_CX}
        y1={HEAD_Y[1] - BLOCK_H / 2}
        x2={DEC_CX}
        y2={OUT_PROB_Y + 8}
        stroke={PAL.arrow}
        strokeWidth={1.4}
        markerEnd="url(#arrow)"
      />
      <text
        x={DEC_CX}
        y={OUT_PROB_Y}
        textAnchor="middle"
        fontFamily={SERIF}
        fontStyle="italic"
        fontSize={13}
        fontWeight={700}
        fill={PAL.ink}
      >
        Output Probabilities
      </text>

      {/* Cross-attention link */}
      <CrossAttentionArrow />

      <Caption />
      <WatermarkBand />
    </g>
  );
}
