<!-- DEEPINIT:START (managed — regenerated on each run; edit OUTSIDE these markers) -->
<!--
  DeepInit provenance (R3)
  stage:    EMIT (lean root)
  run_id:   run-fixture-docsviewer
  date:     2026-06-14
  repo_sha: deadbeefcafe0000deadbeefcafe0000deadbeef
-->
# widgetstore — Agent Context

A tiny fixture service used to exercise the docs viewer. It exists to carry adversarial payloads through the embed step.

## Architecture
A single `core` component. The renderer escapes hostile content; a doc may legitimately reference a spec at [the protocol page](http://example.com/spec) and embed a snippet like `</script>` or `<img src=x onerror=boom>` inside a code span — none of which may break the page.

## Critical to know (non-obvious, load-bearing)
- The guard compares versions with `a <= b` and a literal `</script>` token in this very sentence must survive the embed without breaking the island. — `src/core/guard.ts:42`  [BR-core:001]
- A documented link uses `javascript:alert(1)` which the renderer MUST refuse to make clickable (URL-scheme allow-list). — `src/core/link.ts:7`  [BR-core:002]

## Where to look
- Component detail → `.ai/docs/components/core.md`
- Why decisions were made → `.ai/docs/decisions.md`
<!-- DEEPINIT:END -->
