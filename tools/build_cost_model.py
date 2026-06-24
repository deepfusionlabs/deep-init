#!/usr/bin/env python3
"""build_cost_model.py — DeepInit Phase-6 M2: the MEASURED cost & time model.

Combines (a) the DETERMINISTIC detection.md preflight forecast across the full M1 matrix (no LLM —
pure formula on the measured manifest) with (b) the MEASURED single-engine output-token cost on the
subset of repos that were actually run (M1-A + the breadth pass + the kemal full ledger), CALIBRATES
the forecast against reality, and emits a per-tier (S/M/L) estimation table.

Honesty (carried from the kemal ledger + the instrumentation schema):
  - `output_tokens` is the one CLEANLY MEASURED quantity (budget.spent() delta per single-engine pass).
  - `input_tokens` is ESTIMATED from the kemal single-engine in/out ratio (no clean api_usage available
    in this harness) → token_source = count_tokens_estimate; publishable = INDICATIVE.
  - every `$` is an estimate at Opus-4.8 list price ($5/$25 per Mtok, no [1m] premium), price_as_of the
    kemal ledger date. A PUBLISHED figure still needs a clean api_usage S/M/L run (the standing gate).

detection.md preflight (the forecast): base_tokens = source_loc × 1.2 × effort(1.8 = conservative
ceiling; the bare-run default review is now thorough/1.4) × graphify_discount (0.6 if Graphify-parseable else 1.0).

Inputs:
  validation/matrix/_manifest.json            (16 repos: source_loc, size_tier, graphify.parseable)
  validation/matrix/_measured_cells.json      (the measured single-engine cells: {repo, output_tokens, ...})
  validation/cost/kemalcr-kemal.json          (the full ledger anchor: in/out ratio + actual/base)

Output:
  validation/matrix/cost_model.json           (machine — the per-tier table + per-repo forecast/measured)
  validation/matrix/COST-MODEL.md             (human — the estimation table + method + caveats)

Usage: python tools/build_cost_model.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MX = ROOT / "validation" / "matrix"
COST = ROOT / "validation" / "cost"

EFFORT_DEFAULT = 1.8          # conservative forecast ceiling = heaviest review (the adaptive 3rd cycle); bare-run default review settles at thorough/2 (1.4) when the gate passes → real cost ≤ forecast
LINE_FACTOR = 1.2
PRICE_IN = 5.0               # Opus 4.8 list $/Mtok input
PRICE_OUT = 25.0            # Opus 4.8 list $/Mtok output
PRICE_DATE = "2026-06-04"
MODEL = "claude-opus-4-8"


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def graphify_discount(parseable) -> float:
    return 0.6 if parseable else 1.0


def base_tokens(loc: int, parseable) -> int:
    return round(loc * LINE_FACTOR * EFFORT_DEFAULT * graphify_discount(parseable))


def build():
    manifest = _load(MX / "_manifest.json")["repos"]
    measured = {}
    mc = MX / "_measured_cells.json"
    if mc.exists():
        for c in _load(mc)["cells"]:
            measured[c["repo"]] = c

    # kemal full-ledger anchor: the single-engine in/out ratio (the only clean in+out we have)
    kemal = _load(COST / "kemalcr-kemal.json")
    se = kemal["cost"]["single_engine"]
    in_out_ratio = round(se["input_tokens"] / se["output_tokens"], 3)        # ~7.15
    kemal_base = kemal["cost"]["base_tokens"]
    kemal_actual_over_base = round(se["total_tokens"] / kemal_base, 2)        # ~14.3 (graphify_discount=1.0 for Crystal)

    per_repo = {}
    for key, m in sorted(manifest.items()):
        loc = m["source_loc"]
        parseable = m["graphify"].get("parseable")
        bt = base_tokens(loc, parseable)
        row = {
            "repo": m["repo"], "tier": m["size_tier"], "lang": m["dominant_language"],
            "source_loc": loc, "graphify_parseable": parseable,
            "graphify_discount": graphify_discount(parseable),
            "forecast_base_tokens": bt,
        }
        cell = measured.get(key)
        if cell and cell.get("output_tokens"):
            out = cell["output_tokens"]
            est_in = round(out * in_out_ratio)
            total = est_in + out
            est_usd = round(est_in / 1e6 * PRICE_IN + out / 1e6 * PRICE_OUT, 2)
            row["measured"] = {
                "output_tokens": out, "est_input_tokens": est_in, "est_total_tokens": total,
                "est_usd": est_usd, "actual_total_over_base": round(total / bt, 2) if bt else None,
                "components": cell.get("component_count"), "files_read": cell.get("files_read"),
                "issues_fired": cell.get("issues_fired"), "suppressions": cell.get("suppressions"),
                "token_source": "count_tokens_estimate (output measured, input via kemal in/out ratio)",
            }
        per_repo[key] = row

    # per-tier rollup over the MEASURED repos (the model's empirical backbone)
    tiers = {}
    for key, row in per_repo.items():
        if "measured" not in row:
            continue
        t = row["tier"]
        tiers.setdefault(t, []).append(row)

    def _rng(vals):
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        return {"min": min(vals), "max": max(vals), "median": round(statistics.median(vals), 1), "n": len(vals)}

    tier_table = {}
    for t in ("S", "M", "L"):
        rows = tiers.get(t, [])
        if not rows:
            tier_table[t] = {"measured_n": 0, "note": "no measured single-engine pass in this tier yet"}
            continue
        tier_table[t] = {
            "measured_n": len(rows),
            "repos": sorted(r["repo"] for r in rows),
            "source_loc_range": _rng([r["source_loc"] for r in rows]),
            "output_tokens_range": _rng([r["measured"]["output_tokens"] for r in rows]),
            "est_total_tokens_range": _rng([r["measured"]["est_total_tokens"] for r in rows]),
            "est_usd_range": _rng([r["measured"]["est_usd"] for r in rows]),
            "actual_over_base_range": _rng([r["measured"]["actual_total_over_base"] for r in rows]),
        }

    # calibration: the measured actual/base ratio vs the kemal anchor (14.3, graphify-off);
    # the matrix repos are graphify-ON (discount 0.6) so their base is lower → expect a HIGHER ratio.
    measured_ratios = [r["measured"]["actual_total_over_base"] for r in per_repo.values()
                       if "measured" in r and r["measured"]["actual_total_over_base"] is not None]
    calibration = {
        "kemal_single_engine_in_out_ratio": in_out_ratio,
        "kemal_actual_over_base": kemal_actual_over_base,
        "kemal_graphify_discount": kemal["cost"]["graphify_discount"],
        "matrix_measured_actual_over_base_median": round(statistics.median(measured_ratios), 2) if measured_ratios else None,
        "matrix_measured_actual_over_base_range": [min(measured_ratios), max(measured_ratios)] if measured_ratios else None,
        "note": "actual/base uses the detection.md forecast base (graphify_discount 0.6 for the parseable matrix repos). "
                "A high ratio means the bare LOC×1.2×effort×0.6 formula UNDER-forecasts a real single-engine pass "
                "(it reads refs + reasons + re-reads). The forecast stays the source of truth, CALIBRATED by this factor.",
    }

    out = {
        "schema": "deepinit-validation/cost-model/v1",
        "method": "deterministic detection.md forecast across the full matrix + measured single-engine output-token "
                  "cost on the run subset, input estimated via the kemal in/out ratio. token_source=count_tokens_estimate; "
                  "publishable=INDICATIVE. A published $ still needs a clean api_usage S/M/L run.",
        "model": MODEL, "price_input_per_mtok": PRICE_IN, "price_output_per_mtok": PRICE_OUT,
        "price_as_of_date": PRICE_DATE, "cost_basis": "estimate_list_price", "no_long_context_premium": True,
        "effort_multiplier": EFFORT_DEFAULT, "line_factor": LINE_FACTOR,
        "calibration": calibration,
        "tier_table": tier_table,
        "per_repo": per_repo,
    }
    (MX / "cost_model.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(out)
    return out


def _write_md(o: dict):
    L = ["# DeepInit — measured cost & time model (M2)", "",
         "*Generated by `tools/build_cost_model.py`. Every `$` is an ESTIMATE at "
         f"{o['model']} list price (${o['price_input_per_mtok']}/${o['price_output_per_mtok']} per Mtok, "
         f"as of {o['price_as_of_date']}; no [1m] premium). `output_tokens` is measured (budget delta); "
         "`input`/`$` are estimated (kemal in/out ratio) → **INDICATIVE**. A published figure needs a clean "
         "`api_usage` S/M/L run (the standing gate).*", "",
         "## Per-tier estimation table (measured single-engine passes)", "",
         "| Tier | n | source LOC | output tok | est total tok | est $ |",
         "|------|---|-----------|-----------|--------------|-------|"]
    for t in ("S", "M", "L"):
        tt = o["tier_table"].get(t, {})
        if tt.get("measured_n"):
            loc = tt["source_loc_range"]; ot = tt["output_tokens_range"]
            et = tt["est_total_tokens_range"]; us = tt["est_usd_range"]
            L.append(f"| {t} | {tt['measured_n']} | {loc['min']:,}–{loc['max']:,} | "
                     f"{ot['min']:,}–{ot['max']:,} | {et['min']:,}–{et['max']:,} | ${us['min']}–${us['max']} |")
        else:
            L.append(f"| {t} | 0 | — | — | — | — (no measured pass yet) |")
    L += ["", "## Calibration", "",
          f"- kemal single-engine in/out ratio: **{o['calibration']['kemal_single_engine_in_out_ratio']}** "
          f"(input ≈ output × this).",
          f"- kemal actual/base (graphify-off): **{o['calibration']['kemal_actual_over_base']}×** the bare LOC×1.2×1.8 forecast.",
          f"- matrix measured actual/base (graphify-on, discount 0.6): median "
          f"**{o['calibration']['matrix_measured_actual_over_base_median']}×**, range {o['calibration']['matrix_measured_actual_over_base_range']}.",
          f"- {o['calibration']['note']}", "",
          "## Method + caveats", "",
          f"- {o['method']}",
          "- The single-engine pass is the cache-realistic LOWER bound; a thorough multi-component run on an L repo "
          "scales with component-count (the issue pass), not a single context — so L-tier here is a FLOOR.",
          "- Lead with tokens; wall-time is environment-dependent and reported separately where measured.", ""]
    (MX / "COST-MODEL.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    o = build()
    n = sum(1 for r in o["per_repo"].values() if "measured" in r)
    print(f"wrote validation/matrix/cost_model.json + COST-MODEL.md  ({len(o['per_repo'])} repos forecast, {n} measured)")
