/**
 * Code review — minimal runnable template.
 *
 * Render:
 *   node ../scripts/render.mjs code-review.canvas.tsx --width 1080
 *
 * Demonstrates: FileReview header + DiffGroup (add/del/ctx) + ReviewThread.
 */
import React from "react";
import {
  useHostTheme,
  H1, H2, Text, Tag,
  FileReview, ReviewThread,
  Stack,
} from "qoder/canvas";

type DiffLine = {
  kind?: "ctx" | "add" | "del";
  oldNo?: number | string;
  newNo?: number | string;
  text: string;
};

const FILE_PATH = "src/agent/credential_pool.py";
const FILE_SUMMARY = "Add jittered backoff to refresh path; preserves existing API shape.";

const LINES: DiffLine[] = [
  { kind: "ctx", oldNo: 41, newNo: 41, text: "    def refresh(self, *, force: bool = False) -> None:" },
  { kind: "ctx", oldNo: 42, newNo: 42, text: "        if not force and not self._stale():" },
  { kind: "ctx", oldNo: 43, newNo: 43, text: "            return" },
  { kind: "del", oldNo: 44, newNo: "",  text: "        self._reload_now()" },
  { kind: "add", oldNo: "",  newNo: 44, text: "        delay = _jitter(self._backoff)" },
  { kind: "add", oldNo: "",  newNo: 45, text: "        time.sleep(delay)" },
  { kind: "add", oldNo: "",  newNo: 46, text: "        self._reload_now()" },
  { kind: "ctx", oldNo: 45, newNo: 47, text: "        self._mark_fresh()" },
  { kind: "ctx", oldNo: 46, newNo: 48, text: "" },
  { kind: "ctx", oldNo: 47, newNo: 49, text: "    def _stale(self) -> bool:" },
];

const COMMENTS = [
  {
    author: "reviewer-bot",
    tone: "warning" as const,
    body: "L44: blocking sleep inside a sync method may stall the event loop in async callers; consider asyncio.sleep variant.",
  },
  {
    author: "@paladnix",
    tone: "info" as const,
    body: "Acknowledged. Plan to add an _async_refresh() in the followup PR; keep this one minimal.",
  },
  {
    author: "reviewer-bot",
    tone: "success" as const,
    body: "Sounds good. Marking the thread as resolved once the followup is linked.",
  },
];

export default function CodeReview() {
  const { tokens } = useHostTheme();
  return (
    <g>
      <g transform="translate(40, 0)">
        <H1>PR #482 — Credential refresh backoff</H1>
        <Text y={36} color={tokens.text.tertiary}>
          1 file changed · +3 −1 · risk: low
        </Text>
        <g transform="translate(0, 64)">
          <Tag label="ready-to-merge" tone="success" x={0}   />
          <Tag label="net-io"         tone="info"    x={120} />
          <Tag label="auth-touched"   tone="warning" x={180} />
        </g>
      </g>

      <g transform="translate(40, 110)">
        <FileReview
          filePath={FILE_PATH}
          summary={FILE_SUMMARY}
          lines={LINES}
          width={620}
        />
      </g>

      <g transform="translate(700, 110)">
        <H2>Review thread</H2>
        <g transform="translate(0, 32)">
          <ReviewThread comments={COMMENTS} width={340} />
        </g>
      </g>
    </g>
  );
}
