# report.md — C-REPORT (unified, co-branded Docs + Insights report)

Emits ONE **`.ai/report.html`** — a self-contained, offline, co-branded report
("DeepInit, by Deep Fusion Labs") that **MERGES** the docs reader and the
metrics/issue dashboard into a single artifact with a top-level **Docs** (default)
· **Insights** · **Map** view switch. It supersedes the two separate artifacts (`viewer.md`
C-VIEW + `dashboard.md` C-DASH), which remain legacy until the harness/STATS
cutover. **Read `redaction.md` first:** the embedded corpus + Insights blob pass
through redaction before embed. (Deliberately supersedes the "the two are not
merged" rule — **ADR-019**. The **Map** view IS an interactive component-graph explorer
inside the report — this **overrides** the prior S-8 / ADR-018 "the report is NOT a graph
explorer" boundary — **ADR-024**; R9 issues-never-lean is untouched and all three views are
deep-tier `.ai/` artifacts. Symbol-level / whole-codebase exploration stays out of scope.)

## Hard constraints (AC-7 / AF-6 / S-8)
- **One self-contained file.** Opens from `file://`. **NO view-time network, NO
  CDN, NO external `src`/`href`, no `fetch`/XHR.** This — offline + the strict CSP
  `default-src 'none'` — is the real invariant, **NOT** "zero third-party code".
- **Vendored libraries, inlined (NOT CDN).** Permissively-licensed OSS may be used,
  **vendored into the single file at build time**: markdown-it (Markdown), DOMPurify
  (sanitizer), highlight.js (code), and **Cytoscape.js (MIT)** for the Map view's
  interactive graph. Pinned under `skills/deep-init/assets/vendor/` (see `vendor/VENDOR.md`) and
  inlined by the builder with a `</script>` breakout guard. License is a non-issue
  (MIT/Apache/BSD); the only constraint is no network at view time. The graph lib must
  be **eval-free under the strict CSP** (no `'unsafe-eval'`) — Cytoscape core qualifies;
  do NOT vendor worker/eval-based layout extensions. (Revises the prior zero-dependency
  stance — ADR-019; adds the graph lib — ADR-024.)
- **XSS-safe.** The report embeds arbitrary analyzed-repo text on a `file://` origin.
  Markdown renders via markdown-it `html:false` (raw HTML escaped) + `DOMPurify.sanitize`
  (belt-and-braces); short inline strings use the first-party safe inliner (createElement
  + textContent + URL-scheme allow-list). `file:line` citations and `[ID]` cross-refs are
  linked by walking the rendered DOM (text nodes only, skipping `code`/`pre`/`a`).
- **Deterministic, never LLM-authored.** The HTML/CSS/JS is a static, hand-authored
  template; the builder ONLY injects the data island(s) + the vendored libs (R3
  provenance; regenerated each run, no owned-region protection). The old hand-authored
  `.ai/dashboard.html` (27 lines, non-reproducible, mock metrics) is the anti-pattern
  this kills.
- **Escape-first embed (load-bearing).** The corpus is one
  `<script type="application/json">` island; every `<`/`>` is escaped at embed so an
  analyzed-repo `</script>` cannot break out; `JSON.parse(textContent)` restores them
  (never `eval`/`fetch`).

## How it is built
`tools/build_report.py <output_dir>` reuses `build_docs_viewer`'s tolerant parsers
(one source of truth) for the docs model, adds the Insights data block (severity from
the manifest's authoritative `by_severity`; component risk from
`manifest.components.<name>.metrics` when present, else an honest **"metrics
unavailable"** state with a real documented-files footprint — R1, never fake zeros),
inlines the vendored libs, and injects the JSON island into
`skills/deep-init/assets/report-template.html`. The `build_docs_viewer` parser is **tolerant of every
ledger shape DeepInit emits** — the `## 1. Verified issues` table / a `## Fires` block / top-level
`## ISS-NNN —` issues, and `## ADR-N:` / `### ADR-N —` decisions — so it is genuinely the ONE source of
truth (ISS-010: the former divergent dogfood-only parser in `build_report.py` was removed; the canonical
parser now handles those shapes, pinned by harness §43 G6).

## Views & features
- **Docs** (default landing): overview (project, architecture, component grid,
  "critical to know" facts), per-component pages (markdown-it + highlight.js), the
  ADR/KL decisions timeline, the issue ledger, the grounding index. Left rail (SVG
  icons) + right "on this page" TOC (auto-hidden on overview/short pages — kept on the
  right per the docs convention; NN/g prefers left/in-body, so placement is a one-line
  switch) + scrollspy.
- **Insights**: a KPI strip, a first-party inline-SVG severity donut + ranked risk
  heatmap (honest "unavailable" + footprint when metrics absent), the issue triage
  board (the medium+ anti-alert-fatigue posture preserved), the decisions table, and
  the DB-drift panel (tri-state honesty). A compact static graph preview links to the
  Map view. **No right rail** — a console nav non-pattern.
- **Map** (ADR-024): a first-class, **interactive + navigable** component-dependency
  graph — pan / zoom / drag, hover tooltips (files/exports/degree/risk), a risk filter,
  and search. **Clicking a node opens that component's Docs page** (`#c-<slug>`). Drawn by
  the vendored, inlined Cytoscape.js over the existing Detect-stage `structural-graph.json`
  (node positions precomputed deterministically in `build_report.py` → `preset` layout, so
  the build stays byte-stable; risk tint from the manifest, null when unscored — R1).
  **Honest-degrades** to the "graph unavailable" state with no graph, and to a first-party
  inline-SVG render (with `data-node-id` click-navigation) when the lib can't initialise
  (headless / no canvas). Component-level only — symbol-level/whole-codebase stays out of scope.
- Cross-cutting: a **⌘K command palette**, instant client-side search, dark/light/auto
  theme (DFL navy + lime), a print stylesheet, keyboard shortcuts — all
  `prefers-reduced-motion`-aware.

## Brand
Deep Fusion Labs: lime `#C4E934` + navy `#070E1B`, the layered-diamond app-icon logo
(inline SVG), co-branded masthead + footer (product-forward: **DeepInit** hero +
"by Deep Fusion Labs"). System fonts (no embedded font — keeps the self-contained,
nothing-bundled-but-the-pinned-libs story).

## Template & verification
`skills/deep-init/assets/report-template.html` carries the markup + inline CSS + first-party app
JS + the vendor/data placeholders. Verified by **`tools/smoke_report.mjs`** — a jsdom
headless render test (libs load incl. Cytoscape; Docs/Insights/component pages render;
the **Map view** renders nodes and a node-click navigates to `#c-<component>`; the Map
honest-degrades when no graph; no runtime errors; an XSS payload is neutralized) — plus
self-containment checks (zero off-host refs). The Python harness pins the report in **§67**
(self-contained + deterministic + honest-degrade) and the Map view in **§75** (the Map tab +
`viewMap`, the navigable enriched graph schema, the vendored-inlined + license-clean +
self-contained graph lib, byte-stable determinism), each with a load-bearing mutation. Build
a populated preview with `make report-preview` (or `python tools/build_report.py
validation/dogfooding/oss-kit`) and smoke it with `make report-smoke`.
