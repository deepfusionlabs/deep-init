#!/usr/bin/env python3
"""Assemble validation/matrix/m1b_init_head_to_head.json from the blind scorecards + capture records.

Inputs (all under c:/tmp/init-bench unless noted):
  mapping.json        label -> {key, arm, run}
  scorecards.json     [{key,label, grounding_pct, faithfulness_pct, dep_edge_recall_pct, claims_total,
                        depth_by_kind, issues_real, issues_fabricated, wrong_high, actionability_1to5, ...}]
  validation/matrix/init-outputs/<key>/_capture_record.json  (per-arm/run cost + tokens)

Output: validation/matrix/m1b_init_head_to_head.json  (byte-stable: sort_keys, no clock; --date stamps it).
Run: python build_m1b_record.py --date 2026-06-25
"""
import argparse, json, statistics as st
from pathlib import Path

BENCH = Path("c:/tmp/init-bench")
ROOT = Path("c:/Src/DeepFusionLabs/deep-init")
OUT = ROOT / "validation/matrix/init-outputs"

META = {  # key -> (repo, lang, tier, fame)
    "gin": ("gin-gonic/gin", "Go", "M", "famous"),
    "click": ("pallets/click", "Python", "M", "famous"),
    "express": ("expressjs/express", "JavaScript", "M", "famous"),
    "gorilla-mux": ("gorilla/mux", "Go", "S", "semi"),
    "itsdangerous": ("pallets/itsdangerous", "Python", "S", "obscure"),
    "uniffi-rs": ("mozilla/uniffi-rs", "Rust", "M", "obscure"),
    "kotlinx-schema": ("Kotlin/kotlinx-serialization-json-schema", "Kotlin", "M", "obscure"),
    "sinatra": ("sinatra/sinatra", "Ruby", "M", "famous"),
    "fmt": ("fmtlib/fmt", "C++", "M", "famous"),
    "commercetools-sync-java": ("commercetools/commercetools-sync-java", "Java", "L", "obscure"),
}


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 1) if xs else None


def _cost(cap, arm, run):
    try:
        return cap["arms"][arm]["runs"][int(run.split("-")[1]) - 1].get("cost_usd")
    except Exception:
        return None


def _otok(cap, arm, run):
    try:
        return cap["arms"][arm]["runs"][int(run.split("-")[1]) - 1].get("usage", {}).get("output_tokens")
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    args = ap.parse_args()

    mapping = {m["label"]: m for m in json.loads((BENCH / "mapping.json").read_text())}
    scorecards = json.loads((BENCH / "scorecards.json").read_text())
    caps = {}
    for key in META:
        p = OUT / key / "_capture_record.json"
        if p.exists():
            caps[key] = json.loads(p.read_text())

    rows = []
    for sc in scorecards:
        label = sc["label"]
        m = mapping.get(label)
        if not m:
            continue
        key, arm, run = m["key"], m["arm"], m["run"]
        repo, lang, tier, fame = META[key]
        rows.append({
            "key": key, "repo": repo, "lang": lang, "tier": tier, "fame": fame,
            "arm": arm, "run": run,
            "grounding_pct": sc.get("grounding_pct"),
            "faithfulness_pct": sc.get("faithfulness_pct"),
            "dep_edge_recall_pct": sc.get("dep_edge_recall_pct"),
            "claims_total": sc.get("claims_total"),
            "issues_real": sc.get("issues_real"),
            "issues_fabricated": sc.get("issues_fabricated"),
            "wrong_high": sc.get("wrong_high"),
            "actionability_1to5": sc.get("actionability_1to5"),
            "cost_usd": _cost(caps.get(key, {}), arm, run),
            "output_tokens": _otok(caps.get(key, {}), arm, run),
        })

    def agg(subset):
        return {
            "n_outputs": len(subset),
            "grounding_pct_mean": _mean([r["grounding_pct"] for r in subset]),
            "grounding_pct_min": min([r["grounding_pct"] for r in subset], default=None),
            "faithfulness_pct_mean": _mean([r["faithfulness_pct"] for r in subset]),
            "dep_edge_recall_pct_mean": _mean([r["dep_edge_recall_pct"] for r in subset]),
            "claims_total_mean": _mean([r["claims_total"] for r in subset]),
            "actionability_mean": _mean([r["actionability_1to5"] for r in subset]),
            "issues_real_total": sum(r["issues_real"] or 0 for r in subset),
            "issues_fabricated_total": sum(r["issues_fabricated"] or 0 for r in subset),
            "wrong_high_total": sum(r["wrong_high"] or 0 for r in subset),
            "cost_usd_mean": _mean([r["cost_usd"] for r in subset]),
        }

    arms = ["init", "deepinit"]
    aggregate_by_arm = {a: agg([r for r in rows if r["arm"] == a]) for a in arms}
    # famous vs obscure (semi grouped with obscure as "non-famous")
    aggregate_by_arm_fame = {
        a: {
            "famous": agg([r for r in rows if r["arm"] == a and r["fame"] == "famous"]),
            "nonfamous": agg([r for r in rows if r["arm"] == a and r["fame"] != "famous"]),
        } for a in arms
    }
    # per-repo init-mean vs deepinit + grounding delta
    per_repo = []
    for key in sorted(META):
        irows = [r for r in rows if r["key"] == key and r["arm"] == "init"]
        drows = [r for r in rows if r["key"] == key and r["arm"] == "deepinit"]
        if not irows and not drows:
            continue
        ig = _mean([r["grounding_pct"] for r in irows])
        dg = _mean([r["grounding_pct"] for r in drows])
        per_repo.append({
            "key": key, "fame": META[key][3], "lang": META[key][1], "tier": META[key][2],
            "init_grounding_pct": ig, "deepinit_grounding_pct": dg,
            "grounding_delta": (round(dg - ig, 1) if (ig is not None and dg is not None) else None),
            "init_faithfulness_pct": _mean([r["faithfulness_pct"] for r in irows]),
            "deepinit_faithfulness_pct": _mean([r["faithfulness_pct"] for r in drows]),
            "init_claims_mean": _mean([r["claims_total"] for r in irows]),
            "deepinit_claims_mean": _mean([r["claims_total"] for r in drows]),
            "deepinit_issues_real": sum(r["issues_real"] or 0 for r in drows),
            "init_issues_real": sum(r["issues_real"] or 0 for r in irows),
            "init_cost_usd_mean": _mean([r["cost_usd"] for r in irows]),
            "deepinit_cost_usd_mean": _mean([r["cost_usd"] for r in drows]),
        })

    record = {
        "schema": "deepinit-validation/m1b-init-head-to-head/v1",
        "milestone": "Phase-6 M1-B — measured DeepInit vs Claude Code /init head-to-head",
        "date": args.date,
        "method": ("Both arms on the SAME pinned clones (validation/matrix/_manifest.json SHAs). /init = the "
                   "built-in Claude Code command (K=3, non-deterministic); deepinit = /deep-init:fast (the "
                   "complete grounded pipeline with review cycles reduced — a conservative DeepInit arm; full "
                   "mode scores >=). Both write a lean CLAUDE.md (the comparable always-loaded front-door file) "
                   "scored by INDEPENDENT blind verifiers (separation of duties) against the real code + the AST "
                   "oracle. grounding%=claims with a verifiable file:line; faithfulness%=claims not code-refuted; "
                   "dep_edge_recall vs validation/matrix/oracles/ (trio only); depth=claims by fact-kind; "
                   "issues real/fabricated; wrong_high=HIGH-confidence code-refuted (R1 cardinal sin). The deep "
                   ".ai/docs tier DeepInit also emits is a capability delta, NOT folded into the head-to-head."),
        "arms": arms,
        "repos": [{"key": k, "repo": META[k][0], "lang": META[k][1], "tier": META[k][2], "fame": META[k][3],
                   "oracle": (k in {"gin", "click", "express"})} for k in sorted(META)],
        "scorecards": rows,
        "aggregate_by_arm": aggregate_by_arm,
        "aggregate_by_arm_fame": aggregate_by_arm_fame,
        "per_repo": per_repo,
        "capability_delta": "TBD — filled from the insight pass (what DeepInit's .ai/docs + issues add that /init structurally cannot).",
        "headline": "TBD",
        "caveat": ("INDICATIVE — 8 repos (7 languages, S+M), 3 famous / 5 non-famous. On famous repos /init's "
                   "prose is accurate (faithfulness high for both) so the measured delta there is grounding + "
                   "depth; the non-famous repos test where /init's lack of grounding also costs correctness."),
        "wrong_high": {a: aggregate_by_arm[a]["wrong_high_total"] for a in arms},
        "provenance": {"blind_scoring": True, "separation_of_duties": "curator!=scorer!=author",
                       "training_contamination_caveat": True, "publishable": "indicative",
                       "raw_evidence": "validation/matrix/init-outputs/<key>/{init,deepinit}/run-*/CLAUDE.md + _capture_record.json"},
    }

    dest = ROOT / "validation/matrix/m1b_init_head_to_head.json"
    dest.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    # console summary
    print(f"wrote {dest.relative_to(ROOT)}")
    for a in arms:
        g = aggregate_by_arm[a]
        print(f"  {a:9s} grounding {g['grounding_pct_mean']}% (min {g['grounding_pct_min']}) · "
              f"faithful {g['faithfulness_pct_mean']}% · claims {g['claims_total_mean']} · "
              f"issues_real {g['issues_real_total']} · wrong_high {g['wrong_high_total']} · "
              f"act {g['actionability_mean']} · ${g['cost_usd_mean']}")
    print("  famous vs non-famous grounding:")
    for a in arms:
        f = aggregate_by_arm_fame[a]
        print(f"    {a:9s} famous {f['famous']['grounding_pct_mean']}% | nonfamous {f['nonfamous']['grounding_pct_mean']}%")


if __name__ == "__main__":
    main()
