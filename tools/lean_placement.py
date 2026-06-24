#!/usr/bin/env python3
"""
lean_placement.py — the deterministic reference for R9 tier placement (the lean-tier
issue-exclusion rule). global-rules §R9 + generation.md: issues (ISS- DEFECTS) are
report-only and NEVER enter the lean, always-loaded tier — they live only in the deep
ledger / dashboard / SARIF. Context FACTS (BR-/WF-/IP-/KL-) go lean ONLY when
non-obvious; everything else stays deep.

The subtle invariant generation.md spells out (the "worked example"): the SAME drift
may be a lean *context fact* AND an ISS- *defect* that share a baseline match-key
`(file:line ± symbol)`. When they do, the FACT may go lean (if non-obvious) while the
DEFECT stays deep-only — the two are deduped, never cross-contaminated, and the defect
text is NEVER placed in lean, NEVER duplicated.

This module is exercised by harness §45 over the mini-lean-exclusion fixture (a synthetic
unit oracle complementing the single e2e §40 G3 check).
"""
from __future__ import annotations


def is_issue(finding: dict) -> bool:
    """A DEFECT record — by explicit kind or an ISS- id."""
    return finding.get("kind") == "issue" or str(finding.get("id", "")).startswith("ISS-")


def place(findings: list[dict]) -> dict:
    """Partition findings into lean vs deep per R9.

    Each finding: {id, kind: 'fact'|'issue', non_obvious: bool, match_key, text}.
    Returns {"lean": [ids], "deep": [ids], "lean_keys_with_sibling_defect": [keys]}.
    """
    lean: list[str] = []
    deep: list[str] = []
    # match_keys that a lean FACT already occupies — a defect on the same key is deep-only
    lean_keys: set[str] = set()

    # Pass 1: place facts (lean iff non-obvious); record their match keys.
    for f in findings:
        if is_issue(f):
            continue
        fid = f["id"]
        if f.get("non_obvious"):
            lean.append(fid)
            if f.get("match_key"):
                lean_keys.add(f["match_key"])
        else:
            deep.append(fid)

    # Pass 2: place issues — ALWAYS deep (R9), regardless of any tier hint. A defect that
    # shares a match-key with a lean fact is still emitted deep (the fact carries the lean
    # context; the defect is never duplicated into lean, never cross-contaminated).
    for f in findings:
        if not is_issue(f):
            continue
        deep.append(f["id"])
        # (no-op note: we never add an issue to `lean`; lean_keys is informational —
        #  it proves the fact stays lean while its sibling defect is deep-only.)
    return {"lean": lean, "deep": deep, "lean_keys_with_sibling_defect":
            sorted(lean_keys & {f.get("match_key") for f in findings if is_issue(f)})}


if __name__ == "__main__":
    import json
    import sys
    data = json.load(sys.stdin) if not sys.stdin.isatty() else []
    print(json.dumps(place(data), indent=2))
