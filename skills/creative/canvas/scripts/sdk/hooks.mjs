// Lightweight host bridge hooks.
// The walker invoked by render.mjs does not run a React reconciler, so these
// "hooks" are just plain functions that read module-level state set up by
// the CLI before invoking the canvas component.
//
// Authoring code stays portable: it still imports useHostTheme/useHostLanguage
// from "qoder/canvas" exactly like the original Qoder SDK.

import { lightTokens, darkTokens } from "../runtime/theme.mjs";

let _hostState = {
  mode: "light",
  tokens: lightTokens,
  language: "en",
  rtl: false,
};

/** @internal — called by render.mjs before evaluating the canvas component. */
export function __setHostState(next) {
  _hostState = { ..._hostState, ...next };
}

export function useHostTheme() {
  return { mode: _hostState.mode, tokens: _hostState.tokens };
}

export function useHostLanguage() {
  return {
    language: _hostState.language,
    direction: _hostState.rtl ? "rtl" : "ltr",
  };
}

/**
 * Pick a localized text bundle by current language. Falls back to "en".
 */
export function useLocalizedText(bundle) {
  if (!bundle) return {};
  const lang = _hostState.language;
  return bundle[lang] || bundle.en || Object.values(bundle)[0] || {};
}

// State / action hooks are noops in offline render. Authoring code may call
// them safely; resulting setters do nothing because the SVG output is static.
export function useCanvasState(_key, initial) {
  return [initial, () => {}];
}
export function useCanvasAction(_key) {
  return () => {};
}
export function sendToChat(_payload) {}
export function useSendToChat() {
  return () => {};
}
export function useReviewThreadStore() {
  return {
    threads: [],
    addComment: () => {},
    resolve: () => {},
  };
}

// Hosts that pin the current selected theme during render.
export const __internals = {
  get mode() { return _hostState.mode; },
  get tokens() { return _hostState.tokens; },
  set: __setHostState,
};

// Convenience: switch tokens by mode name.
export function applyTheme(mode) {
  __setHostState({
    mode,
    tokens: mode === "dark" ? darkTokens : lightTokens,
  });
}
