<!--
  DeepInit provenance (R3)
  stage:    EMIT (deep component doc)
  component: core
  run_id:   run-fixture-docsviewer
-->
# core

**Role.** The only component — a version guard plus a link helper.

**Paths.** `src/core/guard.ts` · `src/core/link.ts`

## Guard
- **BR-core:001 — version compare.** The guard treats `a <= b` as "compatible". A hostile snippet `</script><script>steal()</script>` embedded here must render as inert text, never execute. — `src/core/guard.ts:42`

## Link helper
- **BR-core:002 — scheme allow-list.** Only `http:`/`https:`/`mailto:`/`vscode:`/`#` links are made clickable; `javascript:` / `data:text/html` are dropped to plain text. — `src/core/link.ts:7`

## Cross-component edges
- core → (none): this fixture has a single component.
