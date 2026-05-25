// Public SDK entry. Authoring code imports from "qoder/canvas"; render.mjs
// rewrites that bare specifier to point at this file.

export { default } from "react";
export {
  Children, Component, Fragment, PureComponent, StrictMode, Suspense,
  cloneElement, createContext, createElement, createRef, forwardRef,
  isValidElement, lazy, memo, startTransition,
  useCallback, useContext, useDebugValue, useDeferredValue, useEffect,
  useId, useImperativeHandle, useInsertionEffect, useLayoutEffect,
  useMemo, useReducer, useRef, useState, useSyncExternalStore, useTransition,
} from "react";

// Tokens
export {
  canvasTokens, canvasTokensLight,
  canvasTypography, canvasSpacing, canvasRadius,
  canvasFontSize, canvasMotion, layoutStyles,
} from "../runtime/theme.mjs";

// Hooks
export {
  useHostTheme, useHostLanguage, useLocalizedText,
  useCanvasState, useCanvasAction,
  sendToChat, useSendToChat, useReviewThreadStore,
} from "./hooks.mjs";

// Charts
export { BarChart, LineChart, PieChart } from "./charts.mjs";

// Core primitives
export {
  Stack, Row, Grid, Divider, Spacer,
  Text, H1, H2, H3, Code, Link,
  Card, CardHeader, CardBody, CollapsibleCard,
  Button, SendToChatButton, IconButton,
  Tag, Pill,
  Input, TextArea, Checkbox, Switch, Select,
  Table, TableRow, TableCell,
  Delta, Progress, Stat,
  Callout, Banner, Skeleton,
} from "./primitives.mjs";

// Patterns
export {
  DocsSection, MetricsGrid, ReferencePanel,
  RiskCallout, RiskHeatmap, Timeline,
} from "./patterns.mjs";

// Code review
export {
  DiffGroup, ReviewComment, ReviewThread, FileReview, diffAnchorKey,
} from "./code-view.mjs";
