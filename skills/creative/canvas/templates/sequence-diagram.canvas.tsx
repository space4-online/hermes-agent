/**
 * Sequence diagram — minimal runnable template.
 *
 * Render:
 *   node ../scripts/render.mjs sequence-diagram.canvas.tsx --width 960
 *
 * Authoring style: explicit absolute coordinates. Every lane has an x; every
 * message has a `from -> to` and a y. We deliberately avoid auto-layout so the
 * SVG output stays deterministic across runs.
 */
import React from "react";
import { useHostTheme, H1, Text, Tag } from "qoder/canvas";

type Lane = { id: string; label: string; x: number };
type Activation = { lane: string; y1: number; y2: number };
type Message = {
  from: string;
  to: string;
  y: number;
  label: string;
  kind?: "sync" | "async" | "return";
};

const LANES: Lane[] = [
  { id: "user",    label: "User",            x: 120 },
  { id: "gw",      label: "API Gateway",     x: 360 },
  { id: "svc",     label: "Order Service",   x: 600 },
  { id: "db",      label: "Postgres",        x: 840 },
];

const ACTIVATIONS: Activation[] = [
  { lane: "gw",  y1: 110, y2: 290 },
  { lane: "svc", y1: 150, y2: 250 },
  { lane: "db",  y1: 180, y2: 220 },
];

const MESSAGES: Message[] = [
  { from: "user", to: "gw",   y: 110, label: "POST /orders",        kind: "sync"   },
  { from: "gw",   to: "svc",  y: 150, label: "createOrder()",       kind: "sync"   },
  { from: "svc",  to: "db",   y: 180, label: "INSERT order",        kind: "sync"   },
  { from: "db",   to: "svc",  y: 220, label: "ok",                  kind: "return" },
  { from: "svc",  to: "gw",   y: 250, label: "OrderCreated",        kind: "return" },
  { from: "gw",   to: "user", y: 290, label: "201 Created",         kind: "return" },
];

const TOP_LABEL_Y    = 24;
const LANE_LIFELINE  = { y1: 70, y2: 360 };
const CANVAS_HEIGHT  = 420;

export default function SequenceDiagram() {
  const { tokens } = useHostTheme();
  const laneById = Object.fromEntries(LANES.map(l => [l.id, l]));

  return (
    <g>
      {/* Title */}
      <g transform="translate(40, 0)">
        <H1>Order placement — happy path</H1>
        <Text y={36} color={tokens.text.tertiary}>
          POST /orders → API Gateway → Order Service → Postgres
        </Text>
      </g>

      {/* Lane headers + lifelines */}
      {LANES.map(lane => (
        <g key={lane.id} transform={`translate(${lane.x}, 0)`}>
          <rect
            x={-70} y={TOP_LABEL_Y + 36} width={140} height={32}
            rx={tokens.radius.md} ry={tokens.radius.md}
            fill={tokens.bg.elevated} stroke={tokens.stroke.tertiary}
          />
          <text
            x={0} y={TOP_LABEL_Y + 56}
            textAnchor="middle"
            fill={tokens.text.primary}
            fontFamily="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
            fontSize={13} fontWeight={600}
          >{lane.label}</text>
          <line
            x1={0} y1={LANE_LIFELINE.y1} x2={0} y2={LANE_LIFELINE.y2}
            stroke={tokens.stroke.tertiary}
            strokeDasharray="4 4"
          />
        </g>
      ))}

      {/* Activations */}
      {ACTIVATIONS.map((act, i) => {
        const x = laneById[act.lane].x;
        return (
          <rect
            key={i}
            x={x - 5} y={act.y1} width={10} height={act.y2 - act.y1}
            fill={tokens.primary.bg}
            stroke={tokens.primary.border}
          />
        );
      })}

      {/* Messages */}
      <defs>
        <marker
          id="arrow-sync"
          viewBox="0 0 10 10" refX={8} refY={5}
          markerWidth={8} markerHeight={8}
          orient="auto-start-reverse"
        >
          <path d="M0 0 L 10 5 L 0 10 z" fill={tokens.text.secondary} />
        </marker>
        <marker
          id="arrow-return"
          viewBox="0 0 10 10" refX={8} refY={5}
          markerWidth={8} markerHeight={8}
          orient="auto-start-reverse"
        >
          <path d="M0 0 L 10 5 L 0 10 z" fill={tokens.text.tertiary} />
        </marker>
      </defs>

      {MESSAGES.map((msg, i) => {
        const x1 = laneById[msg.from].x;
        const x2 = laneById[msg.to].x;
        const dir = x2 >= x1 ? 1 : -1;
        const isReturn = msg.kind === "return";
        const stroke = isReturn ? tokens.text.tertiary : tokens.text.secondary;
        return (
          <g key={i}>
            <line
              x1={x1 + dir * 6} y1={msg.y}
              x2={x2 - dir * 6} y2={msg.y}
              stroke={stroke}
              strokeWidth={1.4}
              strokeDasharray={isReturn ? "4 3" : undefined}
              markerEnd={isReturn ? "url(#arrow-return)" : "url(#arrow-sync)"}
            />
            <text
              x={(x1 + x2) / 2} y={msg.y - 6}
              textAnchor="middle"
              fill={tokens.text.primary}
              fontFamily="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
              fontSize={12} fontWeight={500}
            >{msg.label}</text>
          </g>
        );
      })}

      {/* Legend */}
      <g transform={`translate(40, ${CANVAS_HEIGHT - 40})`}>
        <Tag label="sync"   tone="info"    x={0}   />
        <Tag label="return" tone="neutral" x={70}  />
        <Tag label="active" tone="accent"  x={150} />
      </g>
    </g>
  );
}
