#!/usr/bin/env bash
# render-previews.sh
# ----------------------------------------------------------------------------
# Re-generate examples/<name>.svg.png from every examples/<name>.svg using
# Chrome headless. PNG pixel dimensions match the SVG viewBox 1:1, so the
# preview is the full figure (no qlmanage square-thumbnail cropping).
#
# Usage: bash scripts/render-previews.sh
# Requires: macOS with Google Chrome installed.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EX="$ROOT/examples"

# Locate a Chromium-family binary.
CHROME=""
for cand in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "$(command -v google-chrome 2>/dev/null || true)" \
  "$(command -v chromium 2>/dev/null || true)"; do
  if [ -n "$cand" ] && [ -x "$cand" ]; then CHROME="$cand"; break; fi
done
if [ -z "$CHROME" ]; then
  echo "ERROR: no Chrome/Chromium binary found." >&2
  exit 1
fi

cd "$EX"
shopt -s nullglob
for svg in *.svg; do
  vb=$(head -c 400 "$svg" | grep -oE 'viewBox="[^"]+"' | head -1 \
         | sed 's/viewBox="//;s/"//')
  W=$(echo "$vb" | awk '{print $3}')
  H=$(echo "$vb" | awk '{print $4}')
  if [ -z "$W" ] || [ -z "$H" ]; then
    echo "skip $svg (no viewBox)"
    continue
  fi
  echo ">> $svg  ${W}x${H}"
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --default-background-color=00000000 \
    --window-size="$W","$H" \
    --screenshot="$EX/$svg.png" \
    "file://$EX/$svg" >/dev/null 2>&1
done

echo "done. $(ls *.svg.png | wc -l | tr -d ' ') preview PNG(s) under $EX"
