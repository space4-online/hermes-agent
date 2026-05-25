// Canvas tokens — light + dark, structurally identical to Qoder canvas-tokens.d.ts.
// All hex values are hand-tuned to mimic VS Code default light/dark themes.
// Authoring code should never reach into raw hex; always read from tokens.*.

const lightStatus = {
  success:        "#1a7f37",
  successHover:   "#196c2e",
  successBg:      "#dafbe1",
  successBgHover: "#c1f0c5",
  successBorder:  "#aceebb",
  warning:        "#9a6700",
  warningHover:   "#7d5300",
  warningBg:      "#fff8c5",
  warningBgHover: "#fae17d",
  warningBorder:  "#eac54f",
  danger:         "#cf222e",
  dangerHover:    "#a40e26",
  dangerBg:       "#ffebe9",
  dangerBgHover:  "#ffcecb",
  dangerBorder:   "#ffaba8",
  info:           "#0969da",
  infoHover:      "#0550ae",
  infoBg:         "#ddf4ff",
  infoBgHover:    "#b6e3ff",
  infoBorder:     "#80ccff",
};

const darkStatus = {
  success:        "#3fb950",
  successHover:   "#56d364",
  successBg:      "#0f2e1a",
  successBgHover: "#13361f",
  successBorder:  "#1f6f3f",
  warning:        "#d29922",
  warningHover:   "#e3b341",
  warningBg:      "#3a2c0c",
  warningBgHover: "#4a3a16",
  warningBorder:  "#7d6826",
  danger:         "#f85149",
  dangerHover:    "#ff7b72",
  dangerBg:       "#2d0f10",
  dangerBgHover:  "#3a1517",
  dangerBorder:   "#762d2d",
  info:           "#58a6ff",
  infoHover:      "#79b8ff",
  infoBg:         "#0d2138",
  infoBgHover:    "#10294a",
  infoBorder:     "#1f5fa0",
};

const sharedRadius = { none: 0, xs: 2, sm: 4, md: 6, lg: 8, xl: 12, full: 9999 };
const sharedSpacing = {
  0.5: 2, 1: 4, 1.5: 6, 2: 8, 2.5: 10, 3: 12, 3.5: 14,
  4: 16, 4.5: 18, 5: 20, 6: 24, 7: 28, 8: 32, 9: 36, 10: 40,
};
const sharedFontSize = {
  xs: "11px", sm: "12px", base: "13px", lg: "14px",
  xl: "16px", "2xl": "18px", "3xl": "20px",
  "4xl": "24px", "5xl": "30px", "6xl": "36px",
};
const sharedTypography = {
  body:  { fontSize: "13px", lineHeight: "20px", fontWeight: 400 },
  small: { fontSize: "12px", lineHeight: "16px", fontWeight: 400 },
  h1:    { fontSize: "24px", lineHeight: "32px", fontWeight: 700 },
  h2:    { fontSize: "18px", lineHeight: "26px", fontWeight: 650 },
  h3:    { fontSize: "14px", lineHeight: "20px", fontWeight: 600 },
  mono:  { fontSize: "12px", lineHeight: "18px", fontWeight: 400 },
};
const sharedShadow = {
  sm: "0 1px 2px rgba(0,0,0,0.06)",
  md: "0 2px 8px rgba(0,0,0,0.10)",
  lg: "0 8px 24px rgba(0,0,0,0.16)",
};
const sharedMotion = {
  durationFast: "120ms",
  durationBase: "200ms",
  durationSlow: "320ms",
  easeIn:     "cubic-bezier(0.4, 0, 1, 1)",
  easeOut:    "cubic-bezier(0, 0, 0.2, 1)",
  easeInOut:  "cubic-bezier(0.4, 0, 0.2, 1)",
  easeLinear: "linear",
};

const lightChart = {
  blue:          "#0969da",
  lightBlue:     "#54aeff",
  teal:          "#0e8a9c",
  cyan:          "#1f9cb0",
  green:         "#1a7f37",
  lightGreen:    "#4ac26b",
  brightOrange:  "#fb8500",
  deepOrange:    "#d3500c",
  goldenYellow:  "#f0b429",
  darkAmber:     "#b07219",
  red:           "#cf222e",
  purple:        "#8250df",
  violet:        "#a371f7",
  warmPink:      "#e15d8a",
  warmPeach:     "#ffa657",
  brown:         "#8a6d3b",
  muted:         "#9a9a9a",
  neutralLine:   "#d0d7de",
  sequence: [
    "#0969da", "#1a7f37", "#bf8700", "#cf222e",
    "#8250df", "#0e8a9c", "#fb8500", "#a371f7",
  ],
};

const darkChart = {
  blue:          "#58a6ff",
  lightBlue:     "#79c0ff",
  teal:          "#39c5cf",
  cyan:          "#56d4dd",
  green:         "#3fb950",
  lightGreen:    "#7ee787",
  brightOrange:  "#ffa657",
  deepOrange:    "#f0883e",
  goldenYellow:  "#e3b341",
  darkAmber:     "#bb8009",
  red:           "#f85149",
  purple:        "#bc8cff",
  violet:        "#d2a8ff",
  warmPink:      "#ff8baf",
  warmPeach:     "#ffb88c",
  brown:         "#c9a96a",
  muted:         "#6e7681",
  neutralLine:   "#30363d",
  sequence: [
    "#58a6ff", "#3fb950", "#d29922", "#f85149",
    "#bc8cff", "#39c5cf", "#ffa657", "#d2a8ff",
  ],
};

export const lightTokens = {
  bg: {
    editor:         "#ffffff",
    chrome:         "#f6f8fa",
    elevated:       "#ffffff",
    sidebar:        "#f6f8fa",
    panel:          "#ffffff",
    overlay:        "rgba(15, 23, 42, 0.45)",
    highlight:      "#fff8c5",
    highlightHover: "#fae17d",
  },
  text: {
    primary:    "#1f2328",
    secondary:  "#4b5563",
    tertiary:   "#6e7781",
    quaternary: "#9ca3af",
    base:       "#1f2328",
    link:       "#0969da",
    onAccent:   "#ffffff",
  },
  stroke: {
    primary:    "#1f2328",
    secondary:  "#6e7781",
    tertiary:   "#d0d7de",
    quaternary: "#eaeef2",
  },
  fill: {
    primary:    "#1f2328",
    secondary:  "#f6f8fa",
    tertiary:   "#eaeef2",
    quaternary: "#f6f8fa",
    disable:    "#e5e7eb",
  },
  accent: {
    primary:      "#0969da",
    control:      "#0969da",
    controlHover: "#0860c4",
    hover:        "#ddf4ff",
    active:       "#b6e3ff",
    focus:        "#218bff",
  },
  primary: {
    color:       "#0969da",
    hover:       "#0860c4",
    active:      "#0550ae",
    bg:          "#ddf4ff",
    bgHover:     "#b6e3ff",
    border:      "#80ccff",
    borderHover: "#54aeff",
    text:        "#0969da",
    textHover:   "#0860c4",
    textActive:  "#0550ae",
    onPrimary:   "#ffffff",
  },
  diff: {
    insertedLine: "#dafbe1",
    removedLine:  "#ffebe9",
    stripAdded:   "#aceebb",
    stripRemoved: "#ffaba8",
    added:        "#1a7f37",
    deleted:      "#cf222e",
    addedText:    "#0a3a14",
    deletedText:  "#67060c",
  },
  syntax: {
    keyword:  "#cf222e",
    string:   "#0a3069",
    number:   "#0550ae",
    comment:  "#6e7781",
    type:     "#953800",
    fn:       "#8250df",
    punct:    "#1f2328",
    property: "#0969da",
    regex:    "#116329",
    plain:    "#1f2328",
  },
  status: lightStatus,
  tone:   lightStatus,
  chart:  lightChart,
  radius: sharedRadius,
  shadow: sharedShadow,
  typography: sharedTypography,
  spacing:    sharedSpacing,
  fontSize:   sharedFontSize,
  motion:     sharedMotion,
};

export const darkTokens = {
  bg: {
    editor:         "#0d1117",
    chrome:         "#010409",
    elevated:       "#161b22",
    sidebar:        "#010409",
    panel:          "#0d1117",
    overlay:        "rgba(2, 6, 23, 0.6)",
    highlight:      "#3a2c0c",
    highlightHover: "#4a3a16",
  },
  text: {
    primary:    "#e6edf3",
    secondary:  "#9ba8b4",
    tertiary:   "#7d8590",
    quaternary: "#6e7681",
    base:       "#e6edf3",
    link:       "#58a6ff",
    onAccent:   "#0d1117",
  },
  stroke: {
    primary:    "#e6edf3",
    secondary:  "#7d8590",
    tertiary:   "#30363d",
    quaternary: "#21262d",
  },
  fill: {
    primary:    "#e6edf3",
    secondary:  "#161b22",
    tertiary:   "#21262d",
    quaternary: "#161b22",
    disable:    "#21262d",
  },
  accent: {
    primary:      "#58a6ff",
    control:      "#58a6ff",
    controlHover: "#79c0ff",
    hover:        "#10294a",
    active:       "#1f5fa0",
    focus:        "#58a6ff",
  },
  primary: {
    color:       "#58a6ff",
    hover:       "#79c0ff",
    active:      "#a5d6ff",
    bg:          "#0d2138",
    bgHover:     "#10294a",
    border:      "#1f5fa0",
    borderHover: "#388bfd",
    text:        "#58a6ff",
    textHover:   "#79c0ff",
    textActive:  "#a5d6ff",
    onPrimary:   "#0d1117",
  },
  diff: {
    insertedLine: "#0f2e1a",
    removedLine:  "#2d0f10",
    stripAdded:   "#1f6f3f",
    stripRemoved: "#762d2d",
    added:        "#3fb950",
    deleted:      "#f85149",
    addedText:    "#aff5b4",
    deletedText:  "#ffa198",
  },
  syntax: {
    keyword:  "#ff7b72",
    string:   "#a5d6ff",
    number:   "#79c0ff",
    comment:  "#8b949e",
    type:     "#ffa657",
    fn:       "#d2a8ff",
    punct:    "#e6edf3",
    property: "#79c0ff",
    regex:    "#7ee787",
    plain:    "#e6edf3",
  },
  status: darkStatus,
  tone:   darkStatus,
  chart:  darkChart,
  radius: sharedRadius,
  shadow: sharedShadow,
  typography: sharedTypography,
  spacing:    sharedSpacing,
  fontSize:   sharedFontSize,
  motion:     sharedMotion,
};

export const canvasTokens = darkTokens;
export const canvasTokensLight = lightTokens;

export const canvasTypography = sharedTypography;
export const canvasSpacing    = sharedSpacing;
export const canvasRadius     = sharedRadius;
export const canvasFontSize   = sharedFontSize;
export const canvasMotion     = sharedMotion;

export const layoutStyles = {
  neutral: { spacingBase: 16, radiusBase: 6,  fontSizeBase: "14px", description: "Balanced default" },
  compact: { spacingBase: 14, radiusBase: 6,  fontSizeBase: "12px", description: "Efficiency-focused" },
  soft:    { spacingBase: 16, radiusBase: 12, fontSizeBase: "14px", description: "Comfort-focused" },
  sharp:   { spacingBase: 14, radiusBase: 0,  fontSizeBase: "12px", description: "Geometric, mono-leaning" },
  dense:   { spacingBase: 12, radiusBase: 4,  fontSizeBase: "12px", description: "Information-dense" },
};

export function pickTokens(mode) {
  return mode === "dark" ? darkTokens : lightTokens;
}
