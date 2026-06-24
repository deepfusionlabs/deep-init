#!/usr/bin/env python3
"""
emit_plan.py — the deterministic reference for the EMIT-COMPLETENESS + CANONICAL-FILE
contract (backlog B1, revised by the "DeepInit owns the front door" model).

DeepInit is run as a Claude Code plugin. Claude Code auto-loads `CLAUDE.md` (root AND
nested along the path to the file being worked on) but does NOT read `AGENTS.md`
natively. So the lean, always-loaded tier's CANONICAL file is **CLAUDE.md** (a
self-contained, content-bearing file — DeepInit is the grounded replacement for
`/init`, whose deliverable IS CLAUDE.md), with **AGENTS.md as a CONDITIONAL cross-tool
export** emitted only when cross-tool consumers (Cursor/Copilot/Windsurf) are present
(or `--canonical=agents`, or forced). A bare run on a Claude-Code repo does NOT emit a
root AGENTS.md (it would be redundant).

The under-emit failure this still fixes (B1): the C7 emitter used a VAGUE predicate for
nested files ("only for components substantial enough … skip trivial ones") with no
objective threshold, so it defaulted to ONE root file and skipped the nested + horizontal
docs. The objective nested rule below is FILE-AGNOSTIC — it decides WHICH components earn
a nested lean file; the canonical basename (CLAUDE.md by default) decides what that file
is called.

Input  — the component registry the emitter holds at C7 (post-Filter): per component
         {name, files, source_lines, has_own_dir, lean_findings}. `name` is REQUIRED and
         UNIQUE (it keys the output path `<name>/<canonical>`). Every other field is
         FAIL-SAFE toward a *reported* skip when absent (R8): missing files/source_lines/
         lean_findings → 0; **missing has_own_dir → False** (→ no_own_dir), never a silent
         emit to a path that may not exist.
         Plus run options: `canonical` ("claude" default | "agents"), the detected
         `cross_tool_consumers` (e.g. ["cursor","copilot","windsurf"]), and
         `force_agents_export` (an explicit flag).
Output — the expected emit manifest: the canonical root + nested lean file basename, the
         nested set + per-skip reason CODE, whether/which horizontal docs emit, and
         whether the CONDITIONAL cross-tool AGENTS.md export + projections emit (+ reason).

Pure + deterministic (no I/O, no clock). Exercised by harness §59 over the
mini-multicomponent fixture; the same thresholds + canonical model are written into
generation.md / horizontal.md / detection.md / SKILL.md so the spec and this reference
cannot drift (§59 G4/G5/G7).
"""
from __future__ import annotations

# The six whole-system docs horizontal.md produces (the canonical set; §59 G6 asserts the
# skill names exactly these so the oracle and the spec stay in lock-step).
HORIZONTAL_DOCS = [
    "technical-dependencies.md",
    "data-layer.md",
    "domain-model.md",
    "functional-workflows.md",
    "cross-references.md",
    "shared-state-conflicts.md",
]

# Objective thresholds (mirrored verbatim in the skill text).
MIN_FILES = 2          # "substantial" size bar — at least 2 source files …
MIN_SOURCE_LINES = 200  # … OR at least 200 source lines (a single tiny file is trivial)
TINY_LINES = 1500      # detection.md's Tiny ceiling — below it a single-component repo folds horizontals

# The canonical lean-tier file per the `--canonical` choice. Default = CLAUDE.md
# (Claude-Code-native; the front door DeepInit owns).
_CANONICAL_FILE = {"claude": "CLAUDE.md", "agents": "AGENTS.md"}


def is_substantial(comp: dict) -> bool:
    """Objective size bar: not a trivial single tiny file."""
    return int(comp.get("files", 0)) >= MIN_FILES or int(comp.get("source_lines", 0)) >= MIN_SOURCE_LINES


def nested_decision(comp: dict, component_count: int) -> tuple[bool, str]:
    """Decide whether a component earns a nested lean file (file-agnostic).

    Returns (emit, reason_code). reason_code is a stable short token — 'emit' when
    nested, else the FIRST failing gate ('single_component' | 'no_own_dir' |
    'trivial_size' | 'no_lean_findings'). The skip reason is always reported (R8).
    """
    if component_count < 2:
        # A single-component repo's "nested" IS the root — don't duplicate.
        return False, "single_component"
    if not comp.get("has_own_dir", False):
        # Root-loose files have nowhere to host a nearest-file context doc.
        # FAIL-SAFE: absent → False → a REPORTED no_own_dir skip (never a silent emit
        # to a path that may not exist). detection.md:90 mandates recording the flag.
        return False, "no_own_dir"
    if not is_substantial(comp):
        return False, "trivial_size"
    if int(comp.get("lean_findings", 0)) < 1:
        # Substantial but carries no non-obvious lean context → the deep component doc
        # + the root pointer suffice; a nested lean file would be empty clutter.
        return False, "no_lean_findings"
    return True, "emit"


def horizontal_decision(registry: list[dict]) -> tuple[bool, str]:
    """Decide whether the six whole-system docs emit (default ON).

    Emitted whenever the repo is multi-component OR above the Tiny threshold. Only a
    Tiny single-component target folds the system view into the root (and says so).
    """
    n = len(registry)
    total_lines = sum(int(c.get("source_lines", 0)) for c in registry)
    if n >= 2:
        return True, "multi_component"
    if total_lines >= TINY_LINES:
        return True, "above_tiny"
    return False, "tiny_single_component"


def agents_export_decision(canonical: str, cross_tool_consumers, force_agents_export: bool) -> tuple[bool, str]:
    """Decide whether the CONDITIONAL cross-tool AGENTS.md export (+ projections) emits.

    On a Claude-Code-native default (canonical=claude, no cross-tool consumers, not
    forced) a root AGENTS.md is REDUNDANT — Claude Code doesn't read it — so it is NOT
    emitted. It emits when AGENTS.md IS the canonical file (--canonical=agents), or a
    cross-tool consumer (Cursor/Copilot/Windsurf) is detected, or an explicit flag forces it.
    """
    if canonical == "agents":
        return True, "canonical_agents"        # AGENTS.md IS the canonical content file
    if cross_tool_consumers:
        return True, "cross_tool_detected"
    if force_agents_export:
        return True, "forced"
    return False, "not_needed"                  # Claude-Code-native: no root AGENTS.md


# ── Existing human-authored front-door file — the ONE emit-time confirmation (B3-confirm) ──
# When the repo already carries a SUBSTANTIAL, HUMAN-AUTHORED front-door file (CLAUDE.md/AGENTS.md with no
# DEEPINIT owned-region markers, above the heavy-file line bar) AND the strategy is still unresolved (no flag/
# config value, not --yes), Emit asks ONE plain-language confirmation instead of silently rewriting it. The
# recommended option is ALWAYS the default (extend / owns-the-front-door); the three buttons map 1:1 to real
# --existing strategies — no invented paths (global-rules R10). Greenfield / a prior-DeepInit owned file /
# a trivial file / --yes all proceed SILENTLY on the owns default (the zero-friction posture).
EXISTING_STRATEGIES = ("skip", "extend", "replace", "side-file")
# Button label → --existing strategy. The prompt is a PRESENTATION layer over the flag (nothing new introduced);
# the recommended option (first) IS the default strategy — never a recommendation that fights the default.
EXISTING_PROMPT_OPTIONS = (
    ("Update my CLAUDE.md", "extend"),     # recommended == default (owned-region + dated .bak)
    ("Preview beside it", "side-file"),    # write CLAUDE.deepinit.md beside the original, untouched
    ("Deep docs only", "skip"),            # .ai/ + report + SARIF only; front-door files untouched
)
EXISTING_RECOMMENDED = "extend"            # MUST equal the default strategy (R10: recommended == default)
HEAVY_FILE_LINES = MIN_SOURCE_LINES        # the >~200-line heavy front-door bar (detection.md), reused


def existing_decision(front_door: dict, resolved_strategy=None, assume_yes: bool = False) -> dict:
    """Decide whether Emit must ASK the one existing-file confirmation, or proceed silently.

    front_door — {present, human_authored, source_lines}: the detected root CLAUDE.md/AGENTS.md state
        (human_authored=False for a prior-DeepInit owned-region file — those regenerate silently).
    resolved_strategy — an already-resolved --existing value (flag or config), or None if unresolved.
    assume_yes — --yes / --no-confirm (suppress the confirmation).

    Returns {prompt, strategy, recommended, reason}. prompt=True ONLY for a present + human-authored + heavy
    file with an unresolved strategy and no --yes; otherwise proceed on `strategy` (the resolved value, else
    the 'extend' owns-the-front-door default). `recommended` is ALWAYS the default (R10). FAIL-SAFE toward the
    non-destructive default — never an invented strategy.
    """
    present = bool(front_door.get("present"))
    human = bool(front_door.get("human_authored"))
    heavy = int(front_door.get("source_lines", 0)) >= HEAVY_FILE_LINES
    if resolved_strategy in EXISTING_STRATEGIES:
        return {"prompt": False, "strategy": resolved_strategy, "recommended": EXISTING_RECOMMENDED, "reason": "resolved"}
    if present and human and heavy and not assume_yes:
        return {"prompt": True, "strategy": None, "recommended": EXISTING_RECOMMENDED, "reason": "heavy_human_authored"}
    why = ("assume_yes" if assume_yes else
           "not_present" if not present else
           "prior_deepinit" if not human else
           "trivial_size")
    return {"prompt": False, "strategy": "extend", "recommended": EXISTING_RECOMMENDED, "reason": why}


def plan(registry: list[dict], canonical: str = "claude",
         cross_tool_consumers=None, force_agents_export: bool = False) -> dict:
    """Compute the full expected emit manifest for a component registry + run options."""
    cross = sorted(cross_tool_consumers or [])
    n = len(registry)
    nested: list[str] = []
    nested_skipped: dict[str, str] = {}
    for comp in registry:
        emit, code = nested_decision(comp, n)
        if emit:
            nested.append(comp["name"])
        else:
            nested_skipped[comp["name"]] = code

    horiz_emit, horiz_code = horizontal_decision(registry)
    canonical_basename = _CANONICAL_FILE.get(canonical, "CLAUDE.md")
    emit_agents, agents_reason = agents_export_decision(canonical, cross, force_agents_export)
    # Under --canonical=agents the content lives in AGENTS.md, but Claude Code does NOT read it natively —
    # so a THIN `CLAUDE.md` whose body is `@AGENTS.md` (the import) must ALSO be written, or the repo
    # auto-loads NOTHING. That thin import is its own root file the Emit-completeness check must verify
    # (a B1-class silent under-emit otherwise). Under the default (claude) the canonical file IS CLAUDE.md,
    # so there is no separate stub.
    import_stub_file = "CLAUDE.md" if canonical == "agents" else None
    import_stub_target = "AGENTS.md" if canonical == "agents" else None
    return {
        "canonical": canonical,
        "root_lean_file": canonical_basename,   # CLAUDE.md (default) | AGENTS.md (--canonical=agents) — always emitted
        "nested_file": canonical_basename,      # nested <component>/<basename>
        "import_stub_file": import_stub_file,   # the thin @import root file (CLAUDE.md under --canonical=agents; else None)
        "import_stub_target": import_stub_target,
        "nested": nested,
        "nested_skipped": nested_skipped,
        "horizontal_emitted": horiz_emit,
        "horizontal_docs": list(HORIZONTAL_DOCS) if horiz_emit else [],
        "horizontal_reason_code": horiz_code,
        "emit_agents_export": emit_agents,      # the CONDITIONAL cross-tool AGENTS.md + projections
        "agents_export_reason": agents_reason,
        "cross_tool_consumers": cross,
    }


if __name__ == "__main__":
    import json
    import sys
    data = json.load(sys.stdin) if not sys.stdin.isatty() else []
    if isinstance(data, dict):
        reg = data.get("registry", [])
        opts = {k: data[k] for k in ("canonical", "cross_tool_consumers", "force_agents_export") if k in data}
        print(json.dumps(plan(reg, **opts), indent=2))
    else:
        print(json.dumps(plan(data), indent=2))
