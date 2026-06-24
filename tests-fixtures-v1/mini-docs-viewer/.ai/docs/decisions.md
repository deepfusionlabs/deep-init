<!--
  DeepInit provenance (R3)
  stage:    ADR (decisions + knowledge log)
  run_id:   run-fixture-docsviewer
-->
# Decisions & Knowledge Log — widgetstore

## ADR-0001: Escape-first rendering of embedded docs
- **Status:** accepted
- **Date:** 2026-06-14
- **Context:** The viewer embeds Markdown from arbitrary analyzed repos, so a snippet could contain `</script>` or `<img onerror=…>`.
- **Decision:** Embed the corpus as an inline JSON island with `<`/`>` escaped to `<`/`>`; render via createElement + textContent on a fixed allow-list.
- **Why:** A `file://`-origin XSS is worse than web; escape-first with no innerHTML is the whole defense.
- **Evidence:** `src/core/guard.ts:42`
- **Consequences:** No sanitizer to keep current; the file is auditable in one read.
- **Certainty:** [HIGH]

## Knowledge Log
- **KL-learning:001** | A literal `</script>` in any doc must be escaped at embed time or it closes the island tag. | `src/core/guard.ts:42` | [HIGH]
