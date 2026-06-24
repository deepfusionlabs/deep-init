#!/usr/bin/env python3
"""
risk_metrics.py — DeepInit IF-5 risk score (the deterministic reference-impl)

Computes the IF-5 risk/priority score for a component from its
(criticality, churn_6mo, coverage_pct, bus_factor) signals, mirroring the single
source-of-truth formula in skills/deep-init/references/issues.md:

    priority = 1000*CRIT + churn_6mo + (100 - coverage_pct) + (50 if bus_factor==1 else 0)
    CRIT = {Core: 3, Supporting: 2, Peripheral: 1}

The skill computes the (criticality, churn, bus_factor, coverage) signals during its
IF-5 pass and persists the result to manifest.json components.<name>.metrics
(schema_version 4, additive) so the report's Insights risk heatmap shows real ranked
data instead of the honest "metrics unavailable" state. This module is the
deterministic mirror the harness pins against issues.md (one source of truth — §19):
the FORMULA lives in the skill prose; this codifies it for the producer + the test.

Honest-degrade (R1 / KL-learning:001 — a confidently-wrong claim is worse than a gap):
- `coverage_pct` is frequently N/A (no coverage integration). When it is None the
  `(100 - coverage_pct)` term is DROPPED and `coverage` is recorded as null — never a
  fabricated 0 (which would read as "0% covered → maximal risk") or 100.
- On thin git history (shallow clone / young repo, flagged by detection.md's
  history-depth preflight) the skill tags the inputs [LOW] and MAY omit the metrics
  block entirely; build_dashboard then renders the honest "metrics unavailable" state
  (report G5) rather than publishing a low-confidence hotspot.

100% local, no network, no clock, no RNG — a pure function, so the harness pins it
byte-deterministically.
"""
from __future__ import annotations

# The IF-5 weights — the SINGLE SOURCE OF TRUTH is issues.md:115; these mirror it and
# the harness (§19) asserts they stay in lockstep. Change issues.md => change here.
CRIT = {"core": 3, "supporting": 2, "peripheral": 1}
CRIT_MULT = 1000
BUS_FACTOR_BONUS = 50


def compute_risk(criticality, churn_6mo, coverage_pct=None, bus_factor=None):
    """Return the IF-5 priority score (float). Mirrors issues.md:115 exactly.

    criticality  : "Core" | "Supporting" | "Peripheral" (case-insensitive).
    churn_6mo    : commits touching the component in the 6-month window (int >= 0).
    coverage_pct : test coverage 0..100, or None when unavailable (term dropped — R1).
    bus_factor   : int author bus-factor, or None; the +50 bonus applies only when == 1.

    The dominant 1000*CRIT term guarantees criticality outranks raw churn (a high-churn
    Peripheral file can never bury a Core one — the not-churn-only property).
    """
    crit = CRIT.get((criticality or "").strip().lower())
    if crit is None:
        raise ValueError(
            f"unknown criticality: {criticality!r} (expected Core/Supporting/Peripheral)"
        )
    score = float(CRIT_MULT * crit)
    score += max(0, int(churn_6mo or 0))
    if coverage_pct is not None:
        score += (100.0 - float(coverage_pct))
    if bus_factor == 1:
        score += BUS_FACTOR_BONUS
    return float(score)


def metrics_block(criticality, churn_6mo, coverage_pct=None, bus_factor=None):
    """Assemble the additive components.<name>.metrics dict (manifest schema_version 4).

    This is the block the skill writes into manifest.json the moment it computes IF-5;
    build_report.build_dashboard reads it for the Insights risk heatmap. `coverage` and
    `bus_factor` stay None (serialized as JSON null) when unavailable — honest-degrade,
    never a fabricated number.
    """
    return {
        "risk": compute_risk(criticality, churn_6mo, coverage_pct, bus_factor),
        "churn": max(0, int(churn_6mo or 0)),
        "bus_factor": bus_factor,
        "coverage": coverage_pct,
        "criticality": criticality,
    }
