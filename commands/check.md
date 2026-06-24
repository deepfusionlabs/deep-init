---
description: Is the context layer still true? 0-token staleness + broken-citation audit (no LLM, CI-friendly). Add --status for the fast hash-only subset.
argument-hint: "[--status]"
---

Run the **deep-init** skill's staleness check — **no LLM, no network, 0 tokens** (any model call here is a bug). This is the unified front door over the two free checks (the `--status` and `--lint` flags stay available for hooks / CI):

1. **Status (deterministic keystone — always runs first).** Execute the status keystone and report its output verbatim:

```
python .ai/deepinit_status.py            # if setup-hooks has installed it into this repo
# else, from the plugin: python skills/deep-init/assets/deepinit_status.py
```

It compares `.ai/docs/current/.file_hashes.json` against the working tree (modified / removed via the Step-0 symmetric set-diff / pending). Exit 0 = fresh, 1 = stale.

2. **Lint (citation + coverage audit — when generated docs exist AND `--status` was NOT passed).** Follow `references/update.md`'s `--lint` flow: per-component fresh/stale/critical staleness, broken-reference (dead `file:line`) detection, ID consistency, and coverage — all by hash/citation comparison, still **0 tokens**. Non-zero exit on a critical/dead citation (the CI gate).

If it reports STALE, offer to run `/deep-init:refresh`. Report the result; **do not modify anything**. See `references/triggers.md` and `references/update.md`.

$ARGUMENTS
