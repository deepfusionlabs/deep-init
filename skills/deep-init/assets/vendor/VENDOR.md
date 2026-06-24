# Vendored libraries (DeepInit report)

These are **pinned, vendored** third-party libraries inlined into `.ai/report.html`
at build time by `tools/build_report.py`. They are **bundled into the single
self-contained file** — the report still loads with **NO network / NO CDN / NO
external `src`** (opens from `file://`), which is the real constraint (offline +
strict CSP), not "zero dependencies". Upgrade deliberately: bump the pinned URL,
re-fetch, re-verify the suite.

| File | Library | Version | License | Source (pinned) |
|------|---------|---------|---------|-----------------|
| `markdown-it.min.js` | markdown-it | 14.1.0 | MIT | https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js |
| `purify.min.js` | DOMPurify | 3.1.7 | Apache-2.0 / MPL-2.0 | https://cdn.jsdelivr.net/npm/dompurify@3.1.7/dist/purify.min.js |
| `highlight.min.js` | highlight.js (common) | 11.10.0 | BSD-3-Clause | https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.10.0/highlight.min.js |
| `cytoscape.min.js` | Cytoscape.js | 3.30.4 | MIT | https://cdn.jsdelivr.net/npm/cytoscape@3.30.4/dist/cytoscape.min.js |

All licenses are permissive (MIT / Apache-2.0 / BSD-3-Clause) and bundling-friendly;
their license headers are preserved in the minified files.

**Why these:** markdown-it = robust, battle-tested Markdown for arbitrary analyzed
repos; DOMPurify = sanitizes the rendered HTML (we embed arbitrary repo text on a
`file://` origin, so XSS-safety is mandatory); highlight.js = professional syntax
highlighting for code blocks. Syntax **colors** come from our own theme-aware CSS
(`--syn-*` vars in the template), not a fixed hljs theme, so code recolors with
light/dark automatically. **Cytoscape.js** powers the interactive, navigable
**Map** view (ADR-024) — pan/zoom/drag + click-a-node-to-open-that-component's-docs.

### Cytoscape under the strict CSP (`default-src 'none'`, no `'unsafe-eval'`)
Cytoscape **core is eval-safe under this report's CSP**. The minified file contains a
single `Function("return this")()` — the standard lodash global-object detection — but
it is **dead code in a browser**: it sits behind `self && self.Object===Object && self`,
which is truthy in any browser (and jsdom) realm, so the `Function` constructor is
**never invoked** and `'unsafe-eval'` is **not** required. (There is no `new Function`,
no `eval(`, no `fetch`/XHR/`<script src>`/`importScripts` — verified at vendor time.)
**Layout discipline:** the Map uses Cytoscape's `preset` layout with node positions
**precomputed deterministically in `tools/build_report.py`** — do **not** vendor any
worker-/eval-based layout extension (`spread`, `cose-bilkent`), which would reintroduce
an eval/`'unsafe-eval'` dependency and break the byte-stable build.
