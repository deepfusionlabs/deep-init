---
description: Refresh only what changed since the last run — incremental re-analysis of the touched components + issue lifecycle, on demand.
---

Run the **deep-init** skill in **update mode** (`--update`). Load `skills/deep-init/SKILL.md` and follow `references/update.md`: Step-0 symmetric set-diff change detection (authoritative; git advisory; deletions caught), DP-1 interface-hash propagation, always re-run the horizontal docs, then re-emit only the affected owned-region files and diff the issue baseline. Do not re-analyse unchanged components.

$ARGUMENTS
