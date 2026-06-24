#!/usr/bin/env python3
"""
progress_model.py — the deterministic reference for DeepInit's IN-RUN progress presentation
(the live "% complete" bar + the honest forecast "time remaining" range). No I/O, no clock —
pure arithmetic/string logic the harness (§98) can exercise without an LLM or a real run.

Why this module exists
----------------------
A full deep-init run is real minutes of work (per-component Extract + Review cycles + the
horizontal pass), but the engine used to show the user NOTHING between the start panel and the
final summary — a long silent wait reads as "stuck". This module pins the live progress line.

The honesty problem it solves
-----------------------------
The DeepInit engine is a Claude instance executing Markdown — it has NO runtime event loop and
NO trustworthy monotonic clock (generation.md's timing-honesty ladder says exactly this). So the
two numbers come from DIFFERENT places, and must be honest about it (global-rules R1):

  * "% complete"  is DETERMINISTIC — a fixed stage-weight table × the fraction of Extract done
    (weighted by component LOC). No clock. Monotonic. Reaches 100 ONLY when Emit finishes.
    `STAGE_WEIGHTS` / `active_weights()` / `percent_complete()`.

  * "time remaining" is a FORECAST — a per-tier baseline wall-time × the remaining fraction
    `(1 - pct)`. NEVER a ticking countdown, NEVER a single fabricated number: `eta_range()`
    returns a (lo, hi) RANGE or None (omit when there is no defensible baseline). The baseline
    is the MEASURED corpus (`TIER_WALLTIME_MIN`, external_metered grade — empty until those runs
    land) or, until then, the WIDE formula band (`FORMULA_TIER_WALLTIME_MIN`, a size-class rough
    guess). The user always sees the word "estimate".

  * the LINE the user reads is plain language (global-rules R10) — `STAGE_VERBS` + `progress_line()`
    say the OUTCOME ("analyzing billing", "writing docs"), never an internal stage code or mechanic.
    The harness scans every emittable string with prompt_ux.prompt_jargon_hits() (§98 G4 reuses §95).

The spec is SKILL.md → "Progress presentation"; extraction.md emits the line at each component
boundary alongside the existing stage-timing stamp. This module is the deterministic mirror the
harness pins in lockstep with that prose (the spec↔impl↔harness triple).
"""
from __future__ import annotations

# ── The stage-weight model (deterministic % complete) ────────────────────────────────────────
# Each stage's share of a typical full run's wall time; Extract dominates and is sub-divided per
# component (by LOC) inside percent_complete(). The numbers are a deliberately ROUND shape prior
# (anchored on the one example timing ledger, validation/cost/_schema-example-ledger.json — NOT a
# measured corpus) and are RECALIBRATED from STATS.timing once the metered S/M/L runs land. They
# MUST sum to exactly 1.0 for a full run; active_weights() renormalizes when a stage is skipped.
STAGE_WEIGHTS: dict[str, float] = {
    "detect": 0.04,                # Detect + the cost/scale estimate (deterministic, ~0 token)
    "plan": 0.01,                  # toposort → Wave 2a/2b
    "extract": 0.45,               # the dominant stage; sub-divided per component (by LOC)
    "horizontal": 0.05,            # the five whole-system docs
    "review": 0.18,                # 2 cycles + an adaptive 3rd — DROPPED in the faster pass
    "adr_kl": 0.05,                # decisions + the knowledge log
    "issues": 0.10,                # the issue pass — DROPPED when issues are off
    "filter_redact_verify": 0.05,  # the deterministic tail (placement · secret/PII gate · citations)
    "emit": 0.07,                  # write the lean + deep tiers, manifest, report (reaches 100 here)
}

# Stage order (the sequence the engine walks; used only for readability/iteration).
STAGE_ORDER: tuple[str, ...] = (
    "detect", "plan", "extract", "horizontal", "review", "adr_kl",
    "issues", "filter_redact_verify", "emit",
)


def active_weights(mode: str = "thorough", issues_on: bool = True) -> dict[str, float]:
    """The stage weights for THIS run, renormalized to sum to 1.0 over the stages that will run.

    mode      — "fast" drops the Review stage (the faster pass skips the review cycles); any other
                value keeps it (the default thorough/deep both review).
    issues_on — False drops the issue pass (--issues=off).

    The active-stage set is frozen at run start from the resolved config, so the denominator never
    grows mid-run — which is what keeps percent_complete() monotonic.
    """
    w = {k: v for k, v in STAGE_WEIGHTS.items()}
    if str(mode).lower() == "fast":
        w.pop("review", None)
    if not issues_on:
        w.pop("issues", None)
    total = sum(w.values())
    if total <= 0:                                  # defensive — never divide by zero
        return {k: 0.0 for k in w}
    return {k: v / total for k, v in w.items()}


def extract_fraction(completed_components, component_locs=None, all_components=None) -> float:
    """The fraction of the Extract stage that is done, in [0, 1].

    Preferred: LOC-weighted — Σ(LOC of completed components) / Σ(LOC of all in-scope components),
    so a 2500-LOC component advances the bar more than a 200-LOC one. component_locs is a
    {name: loc} map over the IN-SCOPE components (its keys are the universe).

    Fallback (honest-degrade, stated): when no per-component LOC is available, an equal-weight
    count — len(completed) / len(all_components). all_components is then the universe.
    """
    completed = list(completed_components or [])
    if component_locs:
        total = sum(component_locs.values())
        if total > 0:
            done = sum(component_locs.get(c, 0) for c in completed)
            return max(0.0, min(1.0, done / total))
    universe = (list(all_components) if all_components
                else (list(component_locs.keys()) if component_locs else []))
    if not universe:
        return 0.0
    done_n = len([c for c in completed if c in universe])
    return max(0.0, min(1.0, done_n / len(universe)))


def percent_complete(completed_stages, completed_components=(), component_locs=None,
                     all_components=None, mode: str = "thorough", issues_on: bool = True,
                     last_pct: float = 0.0) -> float:
    """The deterministic % complete (0.0–100.0), monotonic and clock-free.

    completed_stages     — the set/iterable of stage ids that are FULLY done (e.g. {"detect",
                           "plan"}). The caller maps the run's .deepinit_progress.json `completed{}`
                           map to these ids. "extract" is NOT listed here — its progress is the
                           per-component fraction below (listing it would double-count).
    completed_components — the component names whose Extract is done.
    component_locs       — {name: loc} over the in-scope components (preferred); None ⇒ equal-weight.
    all_components       — the in-scope component universe (needed for the equal-weight fallback).
    mode / issues_on     — select the active-stage set (active_weights()).
    last_pct             — the previously reported %, enforced as a floor (the bar never goes back).

    Reaches 100.0 ONLY when "emit" is in completed_stages (and everything else is done); while Emit
    is pending the result is capped at 99.0 — the structural cure for "stuck at 90%" (the tail
    stages are individually weighted and individually completed, so the bar walks to 100).
    """
    weights = active_weights(mode, issues_on)
    frac = extract_fraction(completed_components, component_locs, all_components)
    done = set(completed_stages or ())
    pct = 0.0
    for stage, weight in weights.items():
        if stage == "extract":
            pct += weight * frac
        elif stage in done:
            pct += weight
    pct *= 100.0
    if "emit" not in done:
        pct = min(pct, 99.0)
    pct = max(pct, float(last_pct or 0.0))
    return round(pct, 1)


# ── The forecast ETA (time remaining) ────────────────────────────────────────────────────────
# MEASURED per-tier baseline wall-time (minutes), as a (lo, hi) range per size tier. Populated from
# STATS.timing.by_tier ONLY once the metered S/M/L corpus (external_metered grade) lands — EMPTY
# until then (the §98 G6 drift guard enforces "empty while STATS.timing is unavailable": no
# fabricated measured baseline). When empty, tier_baseline() falls back to the wide formula band.
TIER_WALLTIME_MIN: dict[str, tuple[float, float]] = {}

# FORMULA-grade fallback baseline (minutes) — a deliberately WIDE size-class rough guess used until
# a tier has measured data. Indicative only (formula_estimate grade): anchored loosely on the one
# example ledger (~7 min for a 7-component tier-S full run) + size scaling, NOT measured. Replaced
# per tier by TIER_WALLTIME_MIN as the metered runs land; the user always sees the word "estimate".
FORMULA_TIER_WALLTIME_MIN: dict[str, tuple[float, float]] = {
    "S": (2.0, 8.0),
    "M": (8.0, 25.0),
    "L": (25.0, 75.0),
}


def tier_baseline(tier):
    """Return (range, source) for a size tier: the MEASURED band if present, else the wide FORMULA
    band, else (None, None) when the tier is unknown. source ∈ {"measured", "formula", None}."""
    if tier in TIER_WALLTIME_MIN:
        return TIER_WALLTIME_MIN[tier], "measured"
    if tier in FORMULA_TIER_WALLTIME_MIN:
        return FORMULA_TIER_WALLTIME_MIN[tier], "formula"
    return None, None


def eta_range(pct, baseline):
    """The estimated time REMAINING as a (lo, hi) range in minutes — or None.

    baseline — the total-run wall-time (lo, hi) range for the detected tier (from tier_baseline()),
               or None when there is no defensible baseline.
    pct      — the deterministic % complete.

    HONESTY CONTRACT (global-rules R1, harness §98 G3): this NEVER returns a single number. It
    returns a 2-tuple range or None — an honest range or an omission, never a fabricated precise
    countdown. The range = baseline × (1 - pct/100), so it shrinks monotonically as % rises (the
    only moving input is the deterministic %, never a stopwatch the engine cannot trust).
    """
    if not baseline:
        return None
    try:
        lo, hi = float(baseline[0]), float(baseline[1])
    except (TypeError, ValueError, IndexError):
        return None
    if lo > hi:
        lo, hi = hi, lo
    remaining = max(0.0, 1.0 - float(pct) / 100.0)
    return (round(lo * remaining, 1), round(hi * remaining, 1))


def format_eta(eta) -> str:
    """Render an eta_range() result as the plain user-facing tail. "" when there is no estimate."""
    if not eta:
        return ""
    lo, hi = eta
    if hi < 1.0:
        return "under a minute left"
    lo_r, hi_r = max(1, round(lo)), round(hi)
    if lo_r >= hi_r:
        return f"~{hi_r} min left (estimate)"
    return f"~{lo_r}-{hi_r} min left (estimate)"


# ── The plain-language line (global-rules R10) ───────────────────────────────────────────────
# Each stage's user-facing verb — the OUTCOME, never an internal stage code or mechanic. "extract"
# carries a {component} slot. Every value here (and every progress_line() output) MUST pass the §95
# banned-term scanner (prompt_ux.prompt_jargon_hits) — harness §98 G4.
STAGE_VERBS: dict[str, str] = {
    "detect": "getting oriented",
    "plan": "getting oriented",
    "extract": "analyzing {component}",
    "horizontal": "mapping the whole project",
    "review": "double-checking the analysis",
    "adr_kl": "capturing key decisions",
    "issues": "checking for problems",
    "filter_redact_verify": "checking citations",
    "emit": "writing docs",
}


def progress_line(stage, pct, eta=None, component=None,
                  component_index=None, component_total=None) -> str:
    """Build the single terse, plain-language progress line the user sees, e.g.
        deep-init: analyzing billing (4 of 7)… 41% — ~6-9 min left (estimate)

    stage            — a STAGE_VERBS key.
    pct              — the % complete (rendered as a whole number).
    eta              — an eta_range() result (a (lo,hi) range or None); None ⇒ no time shown.
    component / index/total — the current component during Extract (shows "(i of N)" when given).
    """
    if stage == "extract":
        if component and component_index and component_total:
            verb = f"analyzing {component} ({component_index} of {component_total})"
        elif component:
            verb = f"analyzing {component}"
        else:
            verb = "analyzing your components"
    else:
        verb = STAGE_VERBS.get(stage, "working")
    line = f"deep-init: {verb}… {float(pct):.0f}%"
    tail = format_eta(eta)
    if tail:
        line += f" — {tail}"
    return line


if __name__ == "__main__":
    import json
    import sys

    # Demo: a mid-Extract checkpoint on a 7-component repo (manual verification / harness entrypoint).
    locs = {"auth": 1200, "billing": 800, "api": 2000, "ui": 1500, "db": 600, "core": 900, "cli": 400}
    done = ["auth", "billing", "api"]
    tier = sys.argv[1] if len(sys.argv) > 1 else "M"
    pct = percent_complete({"detect", "plan"}, done, locs, mode="thorough", issues_on=True)
    base, src = tier_baseline(tier)
    eta = eta_range(pct, base)
    print(json.dumps({
        "weights_sum": round(sum(active_weights().values()), 6),
        "fast_has_review": "review" in active_weights(mode="fast"),
        "extract_is_largest": active_weights()["extract"] == max(active_weights().values()),
        "pct": pct,
        "eta_source": src,
        "eta": eta,
        "line": progress_line("extract", pct, eta, component="api", component_index=3, component_total=7),
    }, indent=2))
