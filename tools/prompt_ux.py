#!/usr/bin/env python3
"""
prompt_ux.py — the deterministic reference for DeepInit's USER-FACING run-time prompts
(global-rules §R10, the "plain, spec'd, no-confabulation" prompt contract). No I/O, no
clock — pure string/decision logic the harness (§95–§97) can exercise without an LLM.

Why this module exists
----------------------
DeepInit's run-time pauses (cost/scope · database · existing front-door file) used to be
only PARTLY specified: only the existing-file confirmation had a pinned template (§74).
The cost and DB pauses had no spec'd option text, so the live engine IMPROVISED them — and
improvised prompts leak DeepInit's internal vocabulary (issue-family codes like "IF-2",
rule refs like "the R7 gate", mechanics like "review cycles", "depth=fast", "ORM-drift",
"SARIF", "managed-region"). R10 forbids exactly that. This module pins:

  1. BANNED_TERM_PATTERNS / prompt_jargon_hits()  — the no-jargon contract (R10): every
     label/header/body shown to a user must be plain language, never an internal code or
     mechanics term. Say the OUTCOME, not the parameter.
  2. before_i_start_cards()                        — the ONE consolidated "Before I start"
     prompt shows ONLY the cards that actually apply, asked ONCE (no upfront-then-emit
     double-ask). Empty list ⇒ the zero-friction default (ask nothing).
  3. cost_pause_decision()                         — pause only when the estimate exceeds
     the ceiling; plain, outcome-worded options; recommended == the deep default (R10).

The DB card's option logic lives in db_gate.py (it reuses the R7 classify_host()); the
existing-file decision lives in emit_plan.existing_decision(). This module owns the
cross-cutting prompt-UX contract that binds them, plus the cost/scope card.
"""
from __future__ import annotations

import re

# ── R10 no-jargon contract ──────────────────────────────────────────────────────────────
# Every user-facing prompt string (AskUserQuestion label / header / option body) is scanned
# against these. Patterns are deliberately NARROW so they fire on the JARGON, never on a
# legitimate plain word: "database", "schema", "production", "deep analysis" are fine;
# "information_schema", "ORM-drift", "the R7 gate", "deep tier" are not. Case-insensitive.
# Mirrored in prose in global-rules.md R10 so the spec and this reference cannot drift.
BANNED_TERM_PATTERNS: list[tuple[str, str]] = [
    # Internal codes / family + rule refs
    (r"\bIF-\d", "issue-family code (IF-N)"),
    (r"\bAF-\d", "anti-fabrication code (AF-N)"),
    (r"\bAC-\d", "acceptance-criterion code (AC-N)"),
    (r"\bDP-\d", "blast-radius code (DP-N)"),
    (r"\bWF-\b|\bWF-[A-Za-z0-9]", "workflow code (WF-)"),
    (r"\bBR-\b|\bBR-[A-Za-z0-9]", "business-rule code (BR-)"),
    (r"\bR\d{1,2}\s+gate\b", "rule-gate ref (e.g. 'R7 gate')"),
    (r"\b[RB]\d{1,2}\b", "bare rule/backlog ref (e.g. R7, B3)"),
    # Implementation-mechanics jargon
    (r"review cycle", "internal mechanic 'review cycle'"),
    (r"grep-first", "internal mechanic 'grep-first'"),
    (r"deep extraction", "internal mechanic 'deep extraction'"),
    (r"\bpreflight\b", "internal mechanic 'preflight'"),
    (r"armed ceiling|cost ceiling", "internal mechanic 'cost ceiling'"),
    (r"wave 0a", "internal stage label 'Wave 0a'"),
    (r"managed[ -]region|owned[ -]region", "internal mechanic 'managed/owned region'"),
    (r"lean tier|deep tier", "internal mechanic 'lean/deep tier'"),
    (r"\bSARIF\b", "internal artifact 'SARIF'"),
    (r"ORM[ -]drift", "internal mechanic 'ORM-drift'"),
    (r"live[ -]drift", "internal mechanic 'live-drift'"),
    (r"information_schema", "internal SQL view 'information_schema'"),
    (r"\bEF migration", "framework-internal noun 'EF migration'"),
    (r"\bNPoco\b", "framework-internal noun 'NPoco'"),
    (r"depth=|review=|--max-cost\b", "raw flag/parameter token"),
    (r"toposort|horizontal pass", "internal pipeline term"),
]


def prompt_jargon_hits(text: str) -> list[str]:
    """Return the sorted labels of every banned term found in `text` (R10 scan).

    Empty list ⇒ the string is plain (R10-clean). Used by the harness to assert every
    spec'd prompt option is jargon-free, and to flag a deliberately-jargony control string.
    """
    if not text:
        return []
    hits = [label for pat, label in BANNED_TERM_PATTERNS if re.search(pat, text, re.IGNORECASE)]
    return sorted(set(hits))


def prompt_is_clean(*strings: str) -> bool:
    """True iff NONE of the given prompt strings contain a banned term (R10)."""
    return not any(prompt_jargon_hits(s) for s in strings)


# ── The ONE consolidated "Before I start" prompt ────────────────────────────────────────
# Shown ONCE after detection/estimate, carrying ONLY the cards that actually apply, in this
# order. Each card is asked here and NEVER re-asked later in the run (the existing-file card,
# when shown here, replaces the emit-time confirmation — no double-ask). An empty list is the
# zero-friction default: a small/DB-less/greenfield repo is asked nothing at all.
CARD_ORDER = ("scope", "database", "existing_file")


def before_i_start_cards(scope_needed: bool = False, db_detected: bool = False,
                         existing_needed: bool = False) -> list[str]:
    """Which cards the single consolidated run-start prompt shows (ordered; [] ⇒ ask nothing)."""
    present = {"scope": bool(scope_needed), "database": bool(db_detected),
               "existing_file": bool(existing_needed)}
    return [c for c in CARD_ORDER if present[c]]


# ── Scope & effort card (the re-framed cost pause) ──────────────────────────────────────
# Plain-language, OUTCOME-worded. The dollar figure is SECONDARY and labeled pay-per-use-only
# (a Claude subscription is not billed per run — see global-rules / SKILL.md). The trigger is
# the cost/scale estimate exceeding the ceiling; the PRESENTATION is scale/effort, not dollars.
# recommended == "proceed" (the deepest analysis is the zero-friction default → R10 rec==default).
COST_PROMPT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Full deep analysis", "proceed"),        # recommended == the deep default
    ("Faster, lighter pass", "fast"),          # a quicker, cheaper pass
    ("Just the main app code", "narrow"),      # narrow to the primary parts
    ("Cancel", "cancel"),
)
COST_RECOMMENDED = "proceed"                   # MUST equal the default action (R10: recommended == default)


def cost_pause_decision(estimated_usd, ceiling=25.0, assume_yes: bool = False) -> dict:
    """Decide whether the scope/effort card is shown, or the run proceeds silently.

    estimated_usd — the pre-run cost/scale estimate (the same signal --max-cost compares).
    ceiling       — the --max-cost guardrail (default 25; a DeepInit setting, NOT a plan limit).
    assume_yes    — --yes / --no-confirm (suppress the pause).

    Returns {prompt, options?, recommended, action?, reason}. prompt=True ONLY when the estimate
    exceeds the ceiling and not --yes; otherwise proceed on the deep default. FAIL-SAFE toward
    proceeding silently (a non-numeric estimate never fabricates a scary pause).
    """
    if assume_yes:
        return {"prompt": False, "action": "proceed", "recommended": COST_RECOMMENDED, "reason": "assume_yes"}
    try:
        over = float(estimated_usd) > float(ceiling)
    except (TypeError, ValueError):
        over = False
    if not over:
        return {"prompt": False, "action": "proceed", "recommended": COST_RECOMMENDED, "reason": "under_ceiling"}
    return {"prompt": True, "options": COST_PROMPT_OPTIONS, "recommended": COST_RECOMMENDED, "reason": "over_ceiling"}


if __name__ == "__main__":
    import json
    import sys
    text = " ".join(sys.argv[1:])
    print(json.dumps({"hits": prompt_jargon_hits(text), "clean": prompt_is_clean(text)}, indent=2))
