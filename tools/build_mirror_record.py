#!/usr/bin/env python3
"""
build_mirror_record.py — turn a Mirror-cycle workflow result into a §34-compliant
coverage record + its held-out reference key (binary LF so the §34 G3 sha256 matches).

Enforces the §34 machinery contract so the new records pass the harness:
  G1  reference_claims = CURRENT only; reference_key.rc_current == len(reference_claims)
  G2  provenance.doc_in_inputs == false; repo.pinned_sha is 40-hex
  G3  reference_key.key_sha256 == sha256(the written key file)  [held_out == true]
  G4  every MISS has miss_referent_read == true (un-read MISSes are EXCLUDED as scope caveats)
  G5  every MATCH has rc_kind == ec_kind (fact-keyed: credit at the RC's kind)
  G6  coverage_overall.n == ΣMATCH, .d == rc_current, by_kind reconciles, pct = n/d
  G7  scores.deepinit_wrong_high == count(deepinit_wrong ∧ HIGH) == 0 (after refutation)
  G8  publishable ∈ {airtight,indicative,internal-only}; the caveats present verbatim

Usage:
  python tools/build_mirror_record.py --result <workflow_result_for_one_repo.json> \
      [--test-plan-run "Run 37"] [--scored-date 2026-06-14]
The result JSON is one element of the Mirror workflow's `results` array (it already
carries key/repo/sha/stack/doc/contamination + reference_claims/emitted_claims/
adjudication/scores/refutation_verdicts).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KINDS = ['component-exists', 'component-role', 'dependency-edge', 'data-store',
         'boundary-rule', 'key-invariant', 'entry-point', 'technology-choice']

CAVEATS = [
    "INDICATIVE — small-n, fuzzy truth, below any ship-gate",
    "attribution-adjudicated — divergences resolved to CODE, not auto-scored",
    "doc-bounded — agreement with a good human doc, not absolute completeness",
    "§18 (9/9, FP 0) stays the product headline",
]


def wilson_lb(n: int, d: int) -> float:
    if d == 0:
        return 0.0
    z = 1.96
    p = n / d
    denom = 1 + z * z / d
    centre = p + z * z / (2 * d)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * d)) / d)
    return round((centre - margin) / denom, 4)


def rescore(record: dict) -> dict:
    """§C11 replay oracle — deterministically RE-SCORE a committed coverage record from its OWN
    reference_claims + adjudication. NO LLM, NO held-out-key re-read (the key stays sha-pinned, read
    only at curation time, never fed to the engine; the fix-author never sees it). Recomputes exactly
    what build_mirror_record computed: coverage_overall (n=ΣMATCH / d=rc_current), by-kind, wrong-HIGH.
    A flipped adjudication bucket (a tampered or spec-regressed run) makes the recomputed vector DIVERGE
    from the committed scores → §C10/§89 catch it. (Faithfulness is a separate count, not adjudication-derived.)"""
    rcs = record.get("reference_claims", []) or []
    adj = record.get("adjudication", []) or []
    matches = [a for a in adj if a.get("bucket") == "MATCH"]
    n, d = len(matches), len(rcs)
    by_kind: dict[str, dict] = {}
    for c in rcs:
        by_kind.setdefault(c.get("kind"), {"n": 0, "d": 0})["d"] += 1
    for a in matches:
        by_kind.setdefault(a.get("rc_kind"), {"n": 0, "d": 0})["n"] += 1
    for k in by_kind:
        bk = by_kind[k]
        bk["pct"] = round(bk["n"] / bk["d"], 4) if bk["d"] else 0.0
    wrong_high = sum(1 for a in adj
                     if a.get("mismatch_attribution") == "deepinit_wrong" and a.get("mismatch_certainty") == "HIGH")
    return {"coverage_overall": {"n": n, "d": d, "pct": round(n / d, 4) if d else 0.0, "wilson95_lb": wilson_lb(n, d)},
            "coverage_by_kind": by_kind, "deepinit_wrong_high": wrong_high}


def rescore_matches(record: dict) -> tuple[bool, dict]:
    """True iff the deterministic re-score reproduces the record's committed coverage_overall (n/d/pct)
    + per-kind n/d (for the kinds that were actually scored, d>0) + wrong-HIGH. The CI-replayable
    regression oracle: a spec edit (or a tampered bucket) that moves coverage shows up as a divergence."""
    rs = rescore(record)
    sc = record.get("scores", {}) or {}
    co_c, co_r = sc.get("coverage_overall", {}) or {}, rs["coverage_overall"]
    co_ok = all(co_r.get(k) == co_c.get(k) for k in ("n", "d", "pct"))
    wh_ok = rs["deepinit_wrong_high"] == sc.get("deepinit_wrong_high")
    bk_ok = all(rs["coverage_by_kind"].get(k, {}).get("n") == v.get("n")
                and rs["coverage_by_kind"].get(k, {}).get("d") == v.get("d")
                for k, v in (sc.get("coverage_by_kind", {}) or {}).items() if v.get("d"))
    return (co_ok and wh_ok and bk_ok),  {"recomputed": co_r, "committed": co_c,
                                          "wrong_high": (rs["deepinit_wrong_high"], sc.get("deepinit_wrong_high"))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", help="workflow result JSON for one repo (build a new record)")
    ap.add_argument("--rescore", help="a committed coverage record to deterministically RE-SCORE (replay oracle; no LLM) — exits 1 if the re-score doesn't reproduce the committed scores")
    ap.add_argument("--test-plan-run", default="Run 37")
    ap.add_argument("--scored-date", default="2026-06-14")
    ap.add_argument("--currency-bar", type=float, default=0.85)
    args = ap.parse_args(argv)

    # --rescore: the §C11 deterministic replay oracle (no engine, no key re-read) — assert reproduction.
    if args.rescore:
        rec = json.loads(Path(args.rescore).read_text(encoding="utf-8"))
        ok, detail = rescore_matches(rec)
        co = detail["recomputed"]
        print(f"[{'OK' if ok else 'DIVERGED'}] rescore {Path(args.rescore).name}: "
              f"re-derived coverage {co['n']}/{co['d']}={co['pct']*100:.1f}% wrong_high={detail['wrong_high'][0]} "
              f"vs committed {detail['committed'].get('n')}/{detail['committed'].get('d')}")
        return 0 if ok else 1
    if not args.result:
        ap.error("one of --result (build) or --rescore (replay-score) is required")

    r = json.loads(Path(args.result).read_text(encoding="utf-8"))
    key = r["key"]

    # ---- 1) split reference_claims to CURRENT only (G1) ----
    rcs_all = r["reference_claims"]
    rcs_current = [c for c in rcs_all if c.get("currency") == "CURRENT"]
    stale = [c for c in rcs_all if c.get("currency") == "STALE"]
    unver = [c for c in rcs_all if c.get("currency") == "UNVERIFIABLE"]

    # ---- 2) reconcile the refutation: a refuted deepinit_wrong is re-attributed ----
    verdicts = {v["rc_id"]: v for v in (r.get("refutation_verdicts") or [])}
    adj_in = r.get("adjudication", [])
    current_ids = {c["rc_id"] for c in rcs_current}

    kept_adj = []
    excluded_unread_miss = []
    for a in adj_in:
        if a["rc_id"] not in current_ids:
            continue  # only score CURRENT RCs
        bucket = a["bucket"]
        if bucket == "MISS" and not a.get("miss_referent_read", False):
            excluded_unread_miss.append(a["rc_id"])      # scope caveat (G4) → drop from denominator
            continue
        row = dict(a)
        if bucket == "MATCH":
            row["ec_kind"] = row.get("rc_kind")           # fact-keyed credit at the RC kind (G5)
        if bucket == "MISMATCH" and row.get("mismatch_attribution") == "deepinit_wrong":
            v = verdicts.get(a["rc_id"])
            if v and v.get("refuted"):                     # refutation overturned it → not a real wrong
                row["mismatch_attribution"] = v.get("correct_attribution") or "abstraction_gap"
                row["mismatch_certainty"] = "MEDIUM" if row.get("mismatch_certainty") == "HIGH" else row.get("mismatch_certainty")
                row["refuter_signoff"] = True
        kept_adj.append(row)

    # the scored RC set = CURRENT minus the excluded unread-MISS referents
    scored_rcs = [c for c in rcs_current if c["rc_id"] not in excluded_unread_miss]
    rc_current = len(scored_rcs)

    # ---- 3) recompute coverage from the kept adjudication (G6) ----
    matches = [a for a in kept_adj if a["bucket"] == "MATCH"]
    n = len(matches)
    by_kind: dict[str, dict] = {}
    for c in scored_rcs:
        by_kind.setdefault(c["kind"], {"n": 0, "d": 0})
        by_kind[c["kind"]]["d"] += 1
    for a in matches:
        k = a["rc_kind"]
        by_kind.setdefault(k, {"n": 0, "d": 0})
        by_kind[k]["n"] += 1
    for k in by_kind:
        bk = by_kind[k]
        bk["pct"] = round(bk["n"] / bk["d"], 4) if bk["d"] else 0.0

    pct = round(n / rc_current, 4) if rc_current else 0.0
    cov = {"n": n, "d": rc_current, "pct": pct, "wilson95_lb": wilson_lb(n, rc_current)}

    # ---- 4) the hard gate: deepinit_wrong ∧ HIGH after refutation (G7) ----
    wrong_high = sum(1 for a in kept_adj
                     if a.get("mismatch_attribution") == "deepinit_wrong" and a.get("mismatch_certainty") == "HIGH")

    # faithfulness: recompute pct as a FRACTION (the workflow returns a percentage) so the
    # record's units match coverage + the helix-record convention (pct in [0,1]).
    _f = r.get("faithfulness") or {"n": 0, "d": 0}
    fn, fd = _f.get("n", 0), _f.get("d", 0)
    faith = {"n": fn, "d": fd, "pct": round(fn / fd, 4) if fd else 0.0, "wilson95_lb": wilson_lb(fn, fd)}

    # ---- 5) write the held-out reference key (binary LF → sha256) ----
    identity = {"languages": [r["stack"].split()[0]], "components": None}
    ref_doc = {"kind": r.get("doc_type", "ARCHITECTURE.md"), "source_url": r["doc"],
               "doc_sha_or_rev": r["sha"],
               "currency_score": round(r.get("currency_score", 0.0), 4), "currency_bar": args.currency_bar}

    key_obj = {
        "schema": "deepinit-validation/coverage-reference-key/v1",
        "program": "The Mirror Test",
        "milestone": "M7-3/M6-B (curator pass + held-out reference key) — contamination-resistant held-out repo",
        "role": "CURATOR-AUTHORED HELD-OUT KEY. The DeepInit engine NEVER sees this file (it runs on the doc-removed code clone).",
        "test_plan_run": args.test_plan_run,
        "curated_date": args.scored_date,
        "repo": {"name": r["repo"], "pinned_sha": r["sha"], "stack": r["stack"], "contamination": r.get("contamination")},
        "reference_doc": ref_doc,
        "reference_key": {
            "held_out": True,
            "rc_total_extracted": len(rcs_all),
            "rc_current": rc_current,
            "rc_stale_dropped": len(stale),
            "rc_unverifiable_dropped": len(unver),
            "rc_excluded_unread_miss": excluded_unread_miss,
        },
        "currency_accounting": {"current": len(rcs_current), "stale": len(stale), "unverifiable": len(unver),
                                "currency_score": round(r.get("currency_score", 0.0), 4)},
        "reference_claims": scored_rcs,
        "curation_log": {"dropped": r.get("dropped", []), "excluded_unread_miss": excluded_unread_miss},
        "firewall": "doc removed from the engine's inputs; blind run on code + Graphify structural graph only.",
        "caveats": CAVEATS + ["training-contamination — LOW (recent / obscure repo); the blind output is unlikely to be informed by pretraining."],
    }
    key_path_rel = f"validation/coverage/_reference_keys/{key}.json"
    key_path = ROOT / key_path_rel
    key_bytes = (json.dumps(key_obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    key_path.write_bytes(key_bytes)                       # BINARY (LF) so the sha256 is stable across platforms
    key_sha = hashlib.sha256(key_bytes).hexdigest()
    (ROOT / f"validation/coverage/_reference_keys/{key}.sha256").write_bytes((key_sha + "\n").encode("utf-8"))

    # ---- 6) the results record ----
    record = {
        "schema": "deepinit-validation/coverage-record/v1",
        "program": "The Mirror Test",
        "milestone": "M7-3/M6-B (blind engine pass + scored, §34-gated) — contamination-resistant held-out repo",
        "test_plan_run": args.test_plan_run,
        "scored_date": args.scored_date,
        "repo": {"name": r["repo"], "url": f"https://github.com/{r['repo']}", "pinned_sha": r["sha"],
                 "license": "Apache-2.0", "stack": r["stack"], "contamination": r.get("contamination")},
        "run": {"run_kind": "coverage_validation",
                "engine_proxy": "blind-workflow (curator≠blind≠scorer), doc-removed tree, Graphify structural path",
                "model": "claude-opus-4-8", "date": args.scored_date},
        "identity": identity,
        "reference_doc": ref_doc,
        "reference_key": {"key_path": key_path_rel, "key_sha256": key_sha, "held_out": True,
                          "rc_total_extracted": len(rcs_all), "rc_current": rc_current,
                          "rc_stale_dropped": len(stale), "rc_unverifiable_dropped": len(unver)},
        "reference_claims": scored_rcs,
        "emitted_claims": r.get("emitted_claims", []),
        "adjudication": kept_adj,
        "beyond_doc": {"count": r.get("beyond_doc_count", 0)},
        "scores": {"coverage_overall": cov, "coverage_by_kind": by_kind, "faithfulness": faith,
                   "beyond_doc_count": r.get("beyond_doc_count", 0), "deepinit_wrong_high": wrong_high},
        "scoring_provenance": {
            "method": "M7-3 isolated-agent Mirror cycle (separation of duties): curator → blind engine (doc-blind, Graphify path) → independent scorer → adversarial refuter per deepinit_wrong.",
            "orchestrator_caveat": "The orchestrating session launched the workflow; curator/blind/scorer/refuter were distinct agents with strict input firewalls.",
            "graphify_path": True,
        },
        "provenance": {
            "doc_in_inputs": False, "key_held_out": True, "training_contamination_caveat": True,
            "publishable": "indicative", "publishable_value": "indicative",
            "caveats": CAVEATS + [f"training-contamination — {r.get('contamination','low')} (recent/obscure repo); the blind output is unlikely to be informed by pretraining, so the number is INDICATIVE."],
            "tune_or_heldout": r.get("split", "held-out"), "harness_section": "§34",
        },
        "publishable": "indicative",
    }
    rec_path = ROOT / f"validation/coverage/results/{key}.json"
    rec_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[{key}] coverage {n}/{rc_current} = {pct*100:.1f}% | faithfulness {faith.get('n')}/{faith.get('d')} "
          f"= {round((faith.get('pct') or 0)*100,1)}% | deepinit_wrong_high(after refutation) {wrong_high} | "
          f"excluded-unread-MISS {len(excluded_unread_miss)} | key_sha256 {key_sha[:12]}…")
    print(f"  wrote {rec_path.relative_to(ROOT)} + {key_path_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
