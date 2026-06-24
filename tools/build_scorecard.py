#!/usr/bin/env python3
"""
build_scorecard.py — the per-run QUALITY SCORECARD (§C9): one byte-stable vector per scored run +
a pooled rollup, recomputed entirely FROM the committed coverage records + cost ledgers (no
hand-typed figure — the §36 spine). It is the feedback loop's input: a single place that says, for
every Mirror/integration run, how good the output was (coverage per fact-kind, faithfulness,
the wrong-HIGH cardinal-sin count, per-stage timing, cost, citation-resolution).

The ONE hard line: `rollup.wrong_high_total == 0`. A run that confidently states a code-refuted fact
(deepinit_wrong ∧ HIGH) is the trust-killer (R1); the rollup must surface zero of them. `assert_clean()`
is the gate the harness (§C9) and any release flow call; it returns False the instant a wrong-HIGH appears.

Pure + deterministic: sorted reads, fixed key order, no clock/RNG — the harness pins the output
byte-for-byte and a spec edit that quietly moved coverage shows up as a scorecard diff (with §C10's
frozen floors catching a regression). Timing/cost degrade to available:false until a matching cost
ledger exists (honest no-data — the metered M7 runs populate them), exactly like the §83 aggregators.

Usage:
  python tools/build_scorecard.py            # regenerate validation/coverage/_scorecard.json
  python tools/build_scorecard.py --check     # assert it regenerates byte-identical AND wrong_high_total==0
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COV_DIR = ROOT / "validation" / "coverage" / "results"
COST_DIR = ROOT / "validation" / "cost"
OUT = ROOT / "validation" / "coverage" / "_scorecard.json"

KINDS = ['component-exists', 'component-role', 'dependency-edge', 'data-store',
         'boundary-rule', 'key-invariant', 'entry-point', 'technology-choice']


def wilson_lb(n: int, d: int) -> float:
    if d == 0:
        return 0.0
    z = 1.96
    p = n / d
    denom = 1 + z * z / d
    centre = p + z * z / (2 * d)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * d)) / d)
    return round((centre - margin) / denom, 4)


def _ledger_for(repo: str, cost_dir: Path) -> dict | None:
    """Find the cost ledger for a repo (owner/name → owner-name.json), if one is committed."""
    cand = cost_dir / (repo.replace("/", "-") + ".json")
    if cand.exists():
        try:
            return json.loads(cand.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _timing_cost(ledger: dict | None) -> dict:
    """Extract the per-stage timing + cost vector from a cost ledger's cost.processing{} block;
    available:false (honest) when there's no ledger or no processing block yet."""
    if not ledger:
        return {"available": False, "reason": "no committed cost ledger for this run yet"}
    cost = ledger.get("cost", {}) or {}
    proc = cost.get("processing")
    out = {"available": bool(proc),
           "wall_time_sec": (proc or {}).get("wall_time_sec") if proc else cost.get("wall_time_sec"),
           "time_source": (proc or {}).get("time_source"),
           "usd_range": cost.get("usd_range") or cost.get("usd"),
           "tokens_total": cost.get("tokens_total")}
    if proc and isinstance(proc.get("stages"), list):
        out["by_stage"] = {s.get("name"): s.get("duration_sec") for s in proc["stages"] if s.get("name")}
    return out


def score_record(rec: dict, ledger: dict | None = None) -> dict:
    """One run → its quality vector. Reads the record's OWN scored figures (it does not re-adjudicate —
    build_mirror_record already scored it under separation of duties); rolls timing/cost from the ledger."""
    scores = rec.get("scores", {}) or {}
    cov = scores.get("coverage_overall", {}) or {}
    by_kind = {}
    for k in KINDS:
        bk = (scores.get("coverage_by_kind", {}) or {}).get(k)
        if bk and bk.get("d"):
            by_kind[k] = {"n": bk.get("n", 0), "d": bk.get("d", 0),
                          "pct": round(bk.get("n", 0) / bk["d"], 4)}
    faith = scores.get("faithfulness", {}) or {}
    cit = rec.get("citation_resolution") or {}
    return {
        "repo": rec.get("repo", {}).get("name"),
        "stack": rec.get("repo", {}).get("stack"),
        "split": rec.get("provenance", {}).get("tune_or_heldout", "held-out"),
        "publishable": rec.get("publishable"),
        "coverage_overall": {"n": cov.get("n", 0), "d": cov.get("d", 0),
                             "pct": cov.get("pct", 0.0), "wilson95_lb": cov.get("wilson95_lb", 0.0)},
        "coverage_by_kind": by_kind,
        "faithfulness": {"n": faith.get("n", 0), "d": faith.get("d", 0),
                         "pct": faith.get("pct", 0.0), "wilson95_lb": faith.get("wilson95_lb", 0.0)},
        "deepinit_wrong_high": int(scores.get("deepinit_wrong_high", 0) or 0),
        "beyond_doc_count": scores.get("beyond_doc_count", 0),
        "citation_resolution": {"checked": cit.get("checked"), "resolved": cit.get("resolved"),
                                "rate": cit.get("rate")} if cit else {"available": False},
        "timing_cost": _timing_cost(ledger),
    }


def _pool(vectors: list[dict], pred=lambda v: True) -> dict:
    """Pool coverage + faithfulness + by-kind across the vectors matching `pred` (Σn/Σd, Wilson LB)."""
    sub = [v for v in vectors if pred(v)]
    cn = sum(v["coverage_overall"]["n"] for v in sub)
    cd = sum(v["coverage_overall"]["d"] for v in sub)
    fn = sum(v["faithfulness"]["n"] for v in sub)
    fd = sum(v["faithfulness"]["d"] for v in sub)
    by_kind = {}
    for k in KINDS:
        n = sum(v["coverage_by_kind"].get(k, {}).get("n", 0) for v in sub)
        d = sum(v["coverage_by_kind"].get(k, {}).get("d", 0) for v in sub)
        if d:
            by_kind[k] = {"n": n, "d": d, "pct": round(n / d, 4), "wilson95_lb": wilson_lb(n, d)}
    return {
        "runs": len(sub),
        "coverage_pooled": {"n": cn, "d": cd, "pct": round(cn / cd, 4) if cd else 0.0, "wilson95_lb": wilson_lb(cn, cd)},
        "faithfulness_pooled": {"n": fn, "d": fd, "pct": round(fn / fd, 4) if fd else 0.0, "wilson95_lb": wilson_lb(fn, fd)},
        "coverage_by_kind_pooled": by_kind,
    }


def build(cov_dir: Path = COV_DIR, cost_dir: Path = COST_DIR) -> dict:
    """Assemble the scorecard from every committed coverage record (sorted → byte-stable)."""
    vectors = []
    for p in sorted(cov_dir.glob("*.json")) if cov_dir.exists() else []:
        if p.name.startswith("_"):
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("schema") != "deepinit-validation/coverage-record/v1":
            continue
        vectors.append(score_record(rec, _ledger_for(rec.get("repo", {}).get("name", ""), cost_dir)))
    vectors.sort(key=lambda v: (v.get("repo") or ""))
    wrong_high_total = sum(v["deepinit_wrong_high"] for v in vectors)
    timing_n = sum(1 for v in vectors if v["timing_cost"].get("available"))
    return {
        "schema": "deepinit-validation/scorecard/v1",
        "program": "Per-run quality scorecard (§C9) — the feedback-loop input",
        "per_run": {v["repo"]: v for v in vectors},
        "rollup": {
            "runs": len(vectors),
            "wrong_high_total": wrong_high_total,           # THE hard line — must be 0 (R1 cardinal sin)
            "all": _pool(vectors),
            "held_out": _pool(vectors, lambda v: v.get("split") == "held-out"),
            "tune": _pool(vectors, lambda v: v.get("split") == "tune"),
            "timing_available_runs": timing_n,
            "timing_note": ("per-stage timing/cost populate as metered runs land a cost ledger; "
                            "0 ledgers matched ⇒ timing degrades to available:false (honest no-data)") if timing_n == 0 else "",
        },
        "provenance": {
            "derived_from": "validation/coverage/results/*.json + validation/cost/*.json",
            "byte_stable": "sorted reads, fixed key order, no clock/RNG — recomputes identically (§36 spine)",
            "hard_gate": "rollup.wrong_high_total == 0 (assert_clean)",
        },
    }


def assert_clean(scorecard: dict) -> bool:
    """The hard gate: the rollup must surface ZERO deepinit_wrong ∧ HIGH facts (R1)."""
    return scorecard.get("rollup", {}).get("wrong_high_total", 1) == 0


def floor_regressions(current: dict, floors: dict) -> list[str]:
    """§C10 coverage non-regression. Return the list of frozen floors a `current` held-out scorecard
    block breaches (pooled or per-kind pct < floor − tolerance). Empty ⇒ no regression. Only kinds the
    current run actually measured (d>0) are gated; the reported figure stays the absolute %. The floor is
    the frozen Wilson95 LB — a spec edit that quietly lowered coverage trips this; honest variance doesn't."""
    tol = floors.get("tolerance", 0.05)
    out: list[str] = []
    cp = (current.get("coverage_pooled", {}) or {}).get("pct", 0.0)
    pf = (floors.get("pooled_held_out", {}) or {}).get("floor", 0.0)
    if cp < pf - tol:
        out.append(f"pooled {cp:.4f} < floor {pf:.4f} − tol {tol}")
    bk = current.get("coverage_by_kind_pooled", {}) or {}
    for k, fl in (floors.get("by_kind", {}) or {}).items():
        cur_k = bk.get(k) or {}
        if cur_k.get("d") and cur_k.get("pct", 0.0) < fl - tol:
            out.append(f"{k} {cur_k.get('pct'):.4f} < floor {fl:.4f} − tol {tol}")
    return out


def _dump(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the per-run quality scorecard (§C9).")
    ap.add_argument("--check", action="store_true",
                    help="assert the committed _scorecard.json regenerates byte-identical AND wrong_high_total==0")
    args = ap.parse_args(argv)
    sc = build()
    text = _dump(sc)
    if args.check:
        ok = True
        if not OUT.exists():
            print("FAIL: validation/coverage/_scorecard.json missing — run without --check first."); return 1
        cur = OUT.read_text(encoding="utf-8")
        if cur != text:
            print("FAIL: scorecard drift — build() no longer regenerates the committed _scorecard.json byte-identical."); ok = False
        if not assert_clean(sc):
            print(f"FAIL: wrong_high_total={sc['rollup']['wrong_high_total']} (must be 0 — a confident code-refuted fact, R1)."); ok = False
        if ok:
            print(f"OK: scorecard byte-stable; {sc['rollup']['runs']} runs; wrong_high_total=0; "
                  f"pooled coverage {sc['rollup']['all']['coverage_pooled']['pct']*100:.1f}%")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({sc['rollup']['runs']} runs, wrong_high_total={sc['rollup']['wrong_high_total']}, "
          f"pooled coverage {sc['rollup']['all']['coverage_pooled']['pct']*100:.1f}%, held-out runs {sc['rollup']['held_out']['runs']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
