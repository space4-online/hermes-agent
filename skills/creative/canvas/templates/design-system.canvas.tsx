/**
 * Design system — minimal runnable template.
 *
 * Render:
 *   node ../scripts/render.mjs design-system.canvas.tsx --width 1100
 *
 * Demonstrates: tokens cheatsheet, primitives gallery, MetricsGrid, Tag tones.
 */
import React from "react";
import {
  useHostTheme,
  H1, H2, H3, Text,
  Card, Tag, Pill, Button, Stat,
  MetricsGrid, Callout, Banner,
  DocsSection,
} from "qoder/canvas";

const TONES = ["info", "success", "warning", "danger", "accent", "neutral"] as const;

export default function DesignSystem() {
  const { tokens, mode } = useHostTheme();

  return (
    <g>
      {/* Title */}
      <g transform="translate(40, 0)">
        <H1>Hermes Canvas — design system</H1>
        <Text y={36} color={tokens.text.tertiary}>
          Token swatches, primitives, and pattern blocks. theme = {mode}
        </Text>
      </g>

      {/* Banner */}
      <g transform="translate(40, 80)">
        <Banner title="All tokens are theme-aware. Always read from useHostTheme().tokens." tone="info" width={1020} />
      </g>

      {/* Color swatches */}
      <g transform="translate(40, 140)">
        <DocsSection title="Status tones" width={1020}>
          <g>
            {TONES.map((tone, i) => (
              <Tag key={tone} label={tone} tone={tone} x={i * 110} y={0} />
            ))}
          </g>
        </DocsSection>
      </g>

      {/* Buttons */}
      <g transform="translate(40, 220)">
        <DocsSection title="Buttons" width={1020}>
          <g>
            <Button label="Primary"   variant="primary"   x={0}   />
            <Button label="Secondary" variant="secondary" x={120} />
            <Button label="Ghost"     variant="ghost"     x={250} />
            <Button label="Danger"    variant="danger"    x={350} />
          </g>
        </DocsSection>
      </g>

      {/* Metrics grid */}
      <g transform="translate(40, 310)">
        <DocsSection title="Metrics grid" width={1020}>
          <g>
            <MetricsGrid
              columns={4}
              width={1020}
              items={[
                { label: "p95 latency", value: "184ms", delta: { value: "-12%", direction: "down" } },
                { label: "error rate",  value: "0.42%",  delta: { value: "+0.04pp", direction: "up" } },
                { label: "throughput",  value: "12.4k/s", delta: { value: "+3%", direction: "up" } },
                { label: "tokens used", value: "82M",     delta: { value: "+1.1M", direction: "up" } },
              ]}
            />
          </g>
        </DocsSection>
      </g>

      {/* Cards */}
      <g transform="translate(40, 460)">
        <DocsSection title="Cards & callouts" width={1020}>
          <g>
            <Card width={320} height={120} accent={tokens.primary.color}>
              <H3>Card · neutral</H3>
              <Text y={28} color={tokens.text.secondary}>Used for grouping related fields or meta blocks.</Text>
              <g transform="translate(0, 60)">
                <Pill label="elevated" tone="neutral" x={0} />
                <Pill label="radius.md" tone="neutral" x={80} />
              </g>
            </Card>
            <g transform="translate(340, 0)">
              <Callout
                title="Use diff tokens for code review surfaces"
                body="tokens.diff.* covers added / removed strips and matching foreground colors. Avoid hardcoding."
                tone="info"
                width={320}
              />
            </g>
            <g transform="translate(680, 0)">
              <Stat label="active sessions" value="248" delta={{ value: "+8", direction: "up" }} width={320} height={120} />
            </g>
          </g>
        </DocsSection>
      </g>
    </g>
  );
}
