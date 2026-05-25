#!/usr/bin/env node
// CLI: render a .canvas.tsx file into a static .svg.
//
// Usage:
//   node render.mjs INPUT.canvas.tsx [-o OUT.svg] [--theme light|dark]
//                                    [--width N]  [--height N]
//
// Flow:
//   1. parse argv
//   2. babel-transform the .canvas.tsx into ESM JS
//   3. rewrite the bare specifier "qoder/canvas" -> local sdk/index.mjs
//   4. write rewritten code to a tmp .mjs and dynamic-import it
//   5. invoke its default export to get the React element tree
//   6. walk the tree -> svg string
//   7. wrap in <svg> envelope, write to OUT
//
// No watchdog, no preview server, no react-dom.

import { promises as fs } from "node:fs";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

import React from "react";
import { renderToSvgString, wrapAsSvgDocument } from "./runtime/jsx-to-svg.mjs";
import { applyTheme } from "./sdk/hooks.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);
const SDK_URL    = pathToFileURL(path.join(__dirname, "sdk", "index.mjs")).href;

const require = createRequire(import.meta.url);

function parseArgs(argv) {
  const opts = {
    input: null, out: null, theme: "light",
    width: 1200, height: null, bg: null,
    format: null,           // "svg" | "png" | "both" | null (auto from -o)
    keepSvg: false,         // when -o is .png, also keep the intermediate .svg
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-o" || a === "--out")        opts.out = argv[++i];
    else if (a === "--theme")               opts.theme = argv[++i];
    else if (a === "--width")               opts.width = Number(argv[++i]);
    else if (a === "--height")              opts.height = Number(argv[++i]);
    else if (a === "--bg")                  opts.bg = argv[++i];
    else if (a === "--format")              opts.format = argv[++i];
    else if (a === "--keep-svg")            opts.keepSvg = true;
    else if (a === "-h" || a === "--help")  opts.help = true;
    else if (!opts.input)                   opts.input = a;
    else throw new Error(`Unknown arg: ${a}`);
  }
  return opts;
}

function usage() {
  return [
    "Usage: node render.mjs INPUT.canvas.tsx [-o OUT.{svg,png}] [--theme light|dark]",
    "                                        [--width N] [--height N] [--bg COLOR]",
    "                                        [--format svg|png|both] [--keep-svg]",
    "",
    "  INPUT        .canvas.tsx (or .canvas.jsx) authoring file",
    "  -o, --out    output path; extension chooses format (.svg default, .png also OK)",
    "  --theme      light | dark   (default: light)",
    "  --width      viewBox width  (default: 1200)",
    "  --height     viewBox height (default: auto from content + padding)",
    "  --bg         background color hex; default uses tokens.bg.editor",
    "  --format     force output kind (svg | png | both). Overrides -o extension.",
    "  --keep-svg   when emitting png, also keep the intermediate .svg next to it",
    "",
    "Notes:",
    "  PNG output is rendered via Chrome headless (matches viewBox 1:1, no cropping).",
    "  Use PNG for IM channels (DingTalk, WeChat, Feishu, Slack) that do not display SVG.",
  ].join("\n");
}

async function loadBabel() {
  // Lazy-load to fail fast with a clear message if deps are missing.
  try {
    const babel = require("@babel/core");
    return babel;
  } catch (err) {
    throw new Error(
      `Missing dependency '@babel/core'. Run 'npm install' inside ` +
      `'${path.relative(process.cwd(), path.join(__dirname, ".."))}' first.\n` +
      `(${err.message})`
    );
  }
}

async function compileToEsm(inputPath) {
  const babel = await loadBabel();
  const result = babel.transformFileSync(inputPath, {
    babelrc: false,
    configFile: false,
    sourceMaps: false,
    presets: [
      [require.resolve("@babel/preset-typescript"), { isTSX: true, allExtensions: true }],
      [require.resolve("@babel/preset-react"), { runtime: "automatic", importSource: "react" }],
    ],
    filename: inputPath,
  });
  if (!result || !result.code) {
    throw new Error(`Babel returned empty output for ${inputPath}`);
  }
  return result.code;
}

function rewriteCanvasImports(code) {
  // Replace `from "qoder/canvas"` with the local SDK file URL so dynamic
  // import can resolve it without configuring a resolver hook.
  return code
    .replace(/from\s+["']qoder\/canvas["']/g, `from "${SDK_URL}"`)
    .replace(/import\s*\(\s*["']qoder\/canvas["']\s*\)/g, `import("${SDK_URL}")`);
}

async function loadComponent(inputPath) {
  const code = await compileToEsm(inputPath);
  const rewritten = rewriteCanvasImports(code);
  // Place the tmp file inside the skill directory so bare specifiers like
  // "react" resolve against this skill's node_modules instead of failing in
  // the system tmp folder.
  const tmpDir = path.join(__dirname, "..", ".canvas-tmp");
  await fs.mkdir(tmpDir, { recursive: true });
  const stamp  = crypto.randomBytes(6).toString("hex");
  const tmp    = path.join(tmpDir, `${path.basename(inputPath, path.extname(inputPath))}-${stamp}.mjs`);
  await fs.writeFile(tmp, rewritten, "utf8");
  let mod;
  try {
    mod = await import(pathToFileURL(tmp).href);
  } finally {
    // Best-effort cleanup; ignore failures so debugging is still possible.
    fs.unlink(tmp).catch(() => {});
  }
  const Component = mod.default;
  if (typeof Component !== "function") {
    throw new Error(`File '${inputPath}' must default-export a function component returning JSX.`);
  }
  return Component;
}

async function main() {
  const opts = parseArgs(process.argv);
  if (opts.help) { console.log(usage()); return; }
  if (!opts.input) {
    console.error(usage());
    process.exit(2);
  }
  const inputAbs = path.resolve(opts.input);
  if (!existsSync(inputAbs)) {
    console.error(`canvas: input not found: ${inputAbs}`);
    process.exit(2);
  }
  if (!/\.canvas\.(tsx|jsx|ts|js)$/.test(inputAbs)) {
    console.warn(`canvas: warning: '${inputAbs}' does not match *.canvas.tsx; treating as JSX anyway.`);
  }

  // Resolve output paths and target format.
  const explicitOut = opts.out ? path.resolve(opts.out) : null;
  let format = opts.format;
  if (!format) {
    if (explicitOut && explicitOut.toLowerCase().endsWith(".png")) format = "png";
    else format = "svg";
  }
  if (!["svg", "png", "both"].includes(format)) {
    console.error(`canvas: unknown --format '${format}' (use svg | png | both)`);
    process.exit(2);
  }

  const stripExt = (p) => p.replace(/\.(svg|png)$/i, "");
  const baseOut = explicitOut
    ? stripExt(explicitOut)
    : stripExt(inputAbs.replace(/\.canvas\.(tsx|jsx|ts|js)$/, ".svg"));
  const svgOut = baseOut + ".svg";
  const pngOut = baseOut + ".png";

  applyTheme(opts.theme === "dark" ? "dark" : "light");

  const Component = await loadComponent(inputAbs);
  const element   = React.createElement(Component, {});
  const body      = renderToSvgString(element);

  const width  = opts.width  || 1200;
  const height = opts.height || estimateHeight(body, opts.width || 1200);
  const bg     = opts.bg || (opts.theme === "dark" ? "#0d1117" : "#ffffff");
  const svg    = wrapAsSvgDocument(body, { width, height, bg });

  await fs.mkdir(path.dirname(svgOut), { recursive: true });
  await fs.writeFile(svgOut, svg, "utf8");

  const wantPng = format === "png" || format === "both";
  const wantSvg = format === "svg" || format === "both" || opts.keepSvg;

  if (wantPng) {
    await svgFileToPng(svgOut, pngOut, { width, height });
    const pstat = await fs.stat(pngOut);
    console.log(
      `canvas: wrote ${pngOut} (${pstat.size} bytes, theme=${opts.theme}, ${width}x${height})`
    );
    if (!wantSvg) {
      await fs.unlink(svgOut).catch(() => {});
    }
  }
  if (!wantPng || wantSvg) {
    console.log(
      `canvas: wrote ${svgOut} (${svg.length} bytes, theme=${opts.theme}, ${width}x${height})`
    );
  }
}

// -- PNG rasterization via Chrome headless ---------------------------------
function findChrome() {
  const env = process.env.CANVAS_CHROME_BIN;
  const candidates = [
    env,
    // macOS desktop installs
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    // Linux container / debian / alpine standard paths
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/lib/chromium/chromium",
    // PATH lookups (containers, custom installs)
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    // Windows
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  ].filter(Boolean);
  for (const cand of candidates) {
    if (cand.includes("/") || cand.includes("\\")) {
      if (existsSync(cand)) return cand;
    } else {
      const probe = spawnSync(process.platform === "win32" ? "where" : "which", [cand], {
        encoding: "utf8",
      });
      if (probe.status === 0) {
        const found = probe.stdout.split(/\r?\n/).find(Boolean);
        if (found) return found.trim();
      }
    }
  }
  // Playwright-managed Chromium (hermes-agent container installs it here
  // via `npx playwright install --only-shell chromium`).
  const pwRoot = process.env.PLAYWRIGHT_BROWSERS_PATH || "/opt/hermes/.playwright";
  const pwHit = findPlaywrightChromium(pwRoot);
  if (pwHit) return pwHit;
  // Some setups also keep a default ~/.cache/ms-playwright/ tree.
  if (process.env.HOME) {
    const homeHit = findPlaywrightChromium(path.join(process.env.HOME, ".cache", "ms-playwright"));
    if (homeHit) return homeHit;
  }
  return null;
}

function findPlaywrightChromium(root) {
  if (!root || !existsSync(root)) return null;
  let entries;
  try { entries = readdirSync(root); } catch { return null; }
  // Prefer headless_shell (smaller, what --only-shell installs); fall back to
  // full chrome. Both accept --screenshot= the same way.
  const subs = [
    { dirPrefix: "chromium_headless_shell-", relBin: "chrome-linux/headless_shell" },
    { dirPrefix: "chromium-",                relBin: "chrome-linux/chrome" },
    { dirPrefix: "chromium_headless_shell-", relBin: "chrome-mac/headless_shell" },
    { dirPrefix: "chromium-",                relBin: "chrome-mac/Chromium.app/Contents/MacOS/Chromium" },
  ];
  for (const { dirPrefix, relBin } of subs) {
    const matches = entries
      .filter(n => n.startsWith(dirPrefix))
      .sort()                        // ascending; pick highest revision last
      .reverse();
    for (const dir of matches) {
      const bin = path.join(root, dir, relBin);
      if (existsSync(bin)) return bin;
    }
  }
  return null;
}

async function svgFileToPng(svgPath, pngPath, { width, height }) {
  const chrome = findChrome();
  if (!chrome) {
    throw new Error(
      "PNG output requires Chrome/Chromium. Install Google Chrome, or set " +
      "CANVAS_CHROME_BIN=/path/to/chrome."
    );
  }
  await fs.mkdir(path.dirname(pngPath), { recursive: true });
  // Use a private user-data-dir inside the skill tree. Avoids
  // "Failed to create a unique user data directory" when the default
  // ~/Library/Application Support/... or /root/... is not writable
  // (sandboxes, read-only HOME, containers running as non-root).
  const userDataDir = path.join(
    __dirname, "..", ".canvas-tmp",
    `chrome-${crypto.randomBytes(6).toString("hex")}`
  );
  await fs.mkdir(userDataDir, { recursive: true });
  const args = [
    "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    "--no-first-run", "--no-default-browser-check",
    // Suppress Crashpad / ProcessSingleton attempts to write under HOME so
    // Chrome works in sandboxes / read-only HOME / non-root containers.
    "--disable-features=Crashpad",
    "--disable-crash-reporter",
    "--disable-breakpad",
    `--crash-dumps-dir=${userDataDir}`,
    `--user-data-dir=${userDataDir}`,
    "--default-background-color=00000000",
    `--window-size=${width},${height}`,
    `--screenshot=${pngPath}`,
    pathToFileURL(svgPath).href,
  ];
  const res = spawnSync(chrome, args, {
    encoding: "utf8",
    // Redirect HOME / XDG / TMPDIR to the per-run dir so Chrome's hardcoded
    // crashpad and ProcessSingleton paths fall inside a writable area, even
    // on locked-down sandboxes / non-root containers.
    env: {
      ...process.env,
      HOME: userDataDir,
      XDG_CONFIG_HOME: userDataDir,
      XDG_CACHE_HOME:  userDataDir,
      TMPDIR:          userDataDir,
    },
  });
  // Best-effort cleanup; OK to leak on failure for debugging.
  fs.rm(userDataDir, { recursive: true, force: true }).catch(() => {});
  if (res.status !== 0 || !existsSync(pngPath)) {
    const detail = (res.stderr || "").split(/\r?\n/).filter(Boolean).slice(-3).join(" | ");
    throw new Error(
      `Chrome headless failed (exit ${res.status}). ${detail || "no stderr"}.`
    );
  }
}

/**
 * Cheap height estimator: scans the rendered body for the largest y/height
 * referenced in transforms and `data-h` annotations, then pads.
 */
function estimateHeight(body, fallbackW) {
  let maxY = 600;
  const re = /translate\(\s*-?\d+(?:\.\d+)?\s*,\s*(-?\d+(?:\.\d+)?)\s*\)/g;
  let m;
  while ((m = re.exec(body)) !== null) {
    const yv = parseFloat(m[1]);
    if (yv > maxY) maxY = yv;
  }
  // also scan explicit y= and height= and data-h
  const yAttr = /\sy="(-?\d+(?:\.\d+)?)"/g;
  while ((m = yAttr.exec(body)) !== null) {
    const yv = parseFloat(m[1]);
    if (yv > maxY) maxY = yv;
  }
  const hAttr = /\s(?:height|data-h)="(-?\d+(?:\.\d+)?)"/g;
  // We can't sum y+height precisely without parsing, so add the largest
  // height we see as bottom padding — good enough for one-page canvases.
  let maxH = 0;
  while ((m = hAttr.exec(body)) !== null) {
    const hv = parseFloat(m[1]);
    if (hv > maxH) maxH = hv;
  }
  return Math.ceil(maxY + maxH + 40);
}

main().catch(err => {
  console.error("canvas: " + (err.stack || err.message));
  process.exit(1);
});
