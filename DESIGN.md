# Design

## Source of truth

- Status: Active
- Last refreshed: 2026-07-28
- Primary product surfaces: Project and Workspace navigation, Workspace Home,
  New Run, Run Detail, Attention, and Command Palette.
- Evidence reviewed:
  - `GOAL.md`
  - `docs/architecture/orca-benchmark-decision.md`
  - `docs/architecture/ade-architecture.md`
  - `docs/architecture/ade-dogfood-report.md`
  - `docs/architecture/evidence/ade-real-runs-attention.png`
  - `docs/architecture/evidence/ade-new-run-multiline.png`
  - `docs/architecture/evidence/ade-run-detail.png`
  - current `src/comx_harness/ade/tk_*.py` presentation
  - Orca product and agent-session documentation at `onorca.dev` and the
    pinned upstream findings already recorded by this repository

## Brand

- Personality: focused, technical, calm, high-agency, and trustworthy.
- Trust signals: explicit provider readiness, visible lifecycle state, durable
  evidence links, and clear read-only versus mutation language.
- Avoid: generic gray desktop forms, bright white data grids, novelty gradients,
  ornamental dashboards, simulated agent activity, and copied Orca trademarks
  or assets.

## Product goals

- Goals:
  - make active work, blocked work, and review needs legible within seconds;
  - make switching Workspace and Run context feel like an agent control center;
  - preserve visible primary actions without requiring keyboard shortcuts;
  - give Codex and OMX equal visual treatment while keeping provider differences
    explicit.
- Non-goals:
  - reproducing Orca feature-for-feature;
  - introducing a second terminal, editor, lifecycle, or orchestration runtime;
  - hiding missing native evidence behind decorative UI.
- Success signals:
  - the first screen communicates current Workspace health and Attention;
  - state color never replaces a textual state label;
  - routine actions remain discoverable and keyboard reachable;
  - visual review no longer reads as a default Tk demo.

## Personas and jobs

- Primary personas: the local repository owner operating repeated Codex and OMX
  work, plus trusted local agents using the same Project and Run truth.
- User jobs:
  - see what is running, waiting, failed, or ready for review;
  - start one safe Run from an exact Plan;
  - inspect evidence and act on Attention;
  - move between repositories and worktrees without remembering sessions.
- Key contexts of use: long desktop sessions, parallel Runs, recovery after
  interruption, and evidence review.

## Information architecture

- Primary navigation: Workspace rail on the left, active surface in the center,
  Attention rail on the right.
- Core screens: Workspace Home, New Run, and Run Detail.
- Content hierarchy:
  1. active Workspace and provider readiness;
  2. Attention and active lifecycle counts;
  3. recent Runs;
  4. evidence and secondary operations.

## Design principles

- Attention over noise: reserve warm color for actionable state.
- State at a glance: combine status dots, text, counts, and row emphasis.
- Dense, not cramped: use an 8-pixel spacing rhythm and compact developer-tool
  controls.
- One dark operating surface: remove default light-widget islands.
- Native truth over theater: unknown stays unknown and unavailable stays
  unavailable.
- Tradeoffs: Tk cannot reproduce Orca's Electron terminal and motion system, so
  prioritize hierarchy, palette, density, and state semantics rather than fake
  fidelity.

## Visual language

- Color:
  - canvas `#0c0f14`;
  - rail `#11151c`;
  - surface `#171c24`;
  - elevated surface `#1d2430`;
  - border `#2a3342`;
  - primary text `#edf1f7`;
  - muted text `#8f9bad`;
  - accent `#7c6cff`;
  - working `#58a6ff`, success `#44d17a`, attention `#f2b84b`, failure
    `#ff6577`.
- Typography: system San Francisco for UI, Menlo for evidence and terminal-like
  content; strong section titles and uppercase muted rail labels.
- Spacing/layout rhythm: 4, 8, 12, 16, and 24 pixels.
- Shape/radius/elevation: Tk-compatible flat surfaces with 1-pixel borders;
  visual grouping comes from tone and spacing rather than fake shadows.
- Motion: none beyond native focus and selection feedback.
- Imagery/iconography: text and Unicode status marks only; no copied Orca assets.

## Components

- Existing components to reuse: `AdeTkShell`, `NewRunView`, `RunDetailView`,
  `AttentionPane`, `AdeRefreshRenderer`, native Treeview, Notebook, and dialogs.
- New/changed components:
  - shared Orca-inspired theme tokens;
  - Workspace metric cards;
  - dark Run and Attention tables with semantic row tags;
  - primary New Run action in the Workspace rail;
  - consistently themed Text, Listbox, palette, and multiline dialog surfaces.
- Variants and states: default, hover/active where ttk supports it, selected,
  disabled, working, attention, succeeded, and failed.
- Token/component ownership: `src/comx_harness/ade/tk_theme.py` owns presentation
  tokens; concept views own their layouts.

## Accessibility

- Target standard: practical WCAG 2.1 AA contrast for text and state surfaces.
- Keyboard/focus behavior: preserve native tab focus, Return activation,
  Notebook traversal, and Command-K/Control-K.
- Contrast/readability: every semantic color is paired with text; body copy uses
  high-contrast neutral text.
- Screen-reader semantics: preserve native Tk widget roles and explicit labels.
- Reduced motion and sensory considerations: no required animation or pulsing.

## Responsive behavior

- Supported breakpoints/devices: desktop windows from 1100×720 upward.
- Layout adaptations: resizable three-pane Panedwindow; center content receives
  the largest weight; long objectives stretch and truncate within tables.
- Touch/hover differences: mouse and keyboard are primary; no hover-only action.

## Interaction states

- Loading: existing content remains visible while refresh runs in the
  background; provider copy communicates checking or unavailable state.
- Empty: explanatory copy and a visible New Run action.
- Error: human-readable status-bar message without losing navigation.
- Success: green state treatment plus explicit succeeded/verified text.
- Disabled: muted contrast and preserved label, especially the Plan-gated Start
  Run button.
- Offline/slow provider: UI remains interactive and presents the last durable
  projection until a fresh snapshot arrives.

## Content voice

- Tone: concise, operational, evidence-first.
- Terminology: use the exact product nouns Project, Workspace, Worktree, Run,
  Agent, Task, Artifact, Evidence, and Attention.
- Microcopy rules: name the unavailable capability and next safe action; avoid
  celebratory or anthropomorphic agent copy.

## Implementation constraints

- Framework/styling system: Python Tk/ttk, no new dependency.
- Design-token constraints: all shared colors and fonts come from
  `tk_theme.py`; individual views may only use semantic tokens.
- Performance constraints: no filesystem, provider, or subprocess work on the
  Tk event-loop thread.
- Compatibility constraints: preserve shared Project/Workspace services, the
  `AdeAgentTools` and `AdeAgentOperations` parity surfaces, the exact-nine
  `HarnessTools` Run lifecycle, detached behavior, and replaceable UI boundary.
- Test/screenshot expectations: run ADE tests, Ruff, Pyrefly, full CI, native
  tests, and capture a real macOS screenshot for visual review.

## Open questions

- [ ] Reassess Tk only after repeated visual or embedded-terminal dogfood proves
      the presentation technology itself blocks the product goal.
- [ ] Decide whether a future embedded terminal is worth adding a host-owned PTY
      boundary; owner: product architecture; impact: high.
