---
description: DeepInit quick pass — a full run with the review cycles skipped (faster, cheaper). Same as `deep-init fast`.
---

Run the **deep-init** skill for a full analysis in **fast** review mode (0 review cycles + the token-saving heuristics). Load `skills/deep-init/SKILL.md`, read `references/global-rules.md` first, then execute the pipeline (Detect → Plan → Extract → Filter → Redact → Verify → Emit, with the report-only issue pass). Equivalent to `deep-init fast`: only the review-cycle count is turned down — everything else keeps the max-quality defaults (issue detection + report + SARIF on). Honour any additional flags the user passes.

$ARGUMENTS
