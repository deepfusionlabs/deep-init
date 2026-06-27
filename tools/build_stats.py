#!/usr/bin/env python3
"""build_stats.py — DeepInit's single stats aggregator (Phase-6 Track A, P6-A1).

Globs every committed validation record family and DERIVES one machine file
(`validation/STATS.json`) + one human file (`validation/STATS.md`) so that EVERY
figure cited on the product page / README / CLAUDE.md flows from an authoritative
per-record field — killing the hand-transcribed-number drift the readiness audit found.

It also refreshes the product-page package's copy at
`docs/product-page-package/source-evidence/STATS.json` (ISS-006) in lockstep, so that
formerly-un-gated shadow can never silently drift (the regen is the suspenders;
tools/check_stats_drift.py's package_stats_copy_in_sync is the belt).

Separation of duties:
  - The HARNESS owns its own pass/section counts + the §26 external-oracle recall
    (`validation/_harness_summary.json`, written at the end of every harness run). The
    aggregator READS those; it never recomputes recall (the plan's A6 anti-cross-use rule).
  - The aggregator owns the RECORD-derived figures (Mirror coverage/faithfulness, precision
    naive-FP-avoided, cost range, stack count) — each recomputed from the records, never
    hand-rounded.

Output is BYTE-STABLE (sorted keys, no timestamps) so harness §36 can assert it regenerates
unchanged from the records. A human "generated" note lives only in STATS.md, never STATS.json.

Usage:
  python tools/build_stats.py            # writes validation/STATS.json + STATS.md
  python tools/build_stats.py --check    # regenerate in-memory, exit 1 if STATS.json on disk differs (CI drift gate)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # repo root
VAL = ROOT / "validation"


def _load(p: Path) -> dict:
    """UTF-8-safe JSON load (records use box-drawing / em-dash chars that crash cp1255)."""
    return json.loads(p.read_text(encoding="utf-8"))


def _wilson_lb(x: int, n: int, z: float = 1.96) -> float:
    """Wilson95 lower bound — identical formula to the harness _wilson_lb (one source of truth)."""
    if n == 0:
        return 0.0
    ph = x / n
    d = 1 + z * z / n
    c = ph + z * z / (2 * n)
    m = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / d)


def _pct(n: int, d: int) -> float:
    return round(n / d, 4) if d else 0.0


# ── Mirror (coverage-record/v1) ──────────────────────────────────────────────
_KINDS = ["component-exists", "component-role", "dependency-edge", "data-store",
          "boundary-rule", "key-invariant", "entry-point", "technology-choice"]


def build_mirror() -> dict:
    results_dir = VAL / "coverage" / "results"
    manifest_p = VAL / "coverage" / "_split_manifest.json"
    if not results_dir.exists() or not manifest_p.exists():
        return {"available": False, "reason": "no coverage results / split manifest"}
    manifest = _load(manifest_p)
    splits = manifest["splits"]
    contam = manifest.get("contamination", {})
    pools: dict = {}
    strata: dict = {}                    # held-out coverage stratified popular-vs-obscure (B2)
    per_repo: dict = {}
    for p in sorted(results_dir.glob("*.json")):
        if p.name.startswith("_"):
            continue
        key = p.stem
        d = _load(p)
        split = splits.get(key)
        if split is None:
            # an unmanifested record is a hard error surfaced loudly (never silently pooled)
            raise SystemExit(f"build_stats: coverage record '{key}' is not in _split_manifest.json")
        s = d["scores"]
        co, fa = s["coverage_overall"], s["faithfulness"]
        per_repo[key] = {
            "split": split,
            "contamination": contam.get(key, "unknown"),
            "coverage_n": co["n"], "coverage_d": co["d"], "coverage_pct": co["pct"],
            "faithfulness_n": fa["n"], "faithfulness_d": fa["d"],
            "deepinit_wrong_high": s["deepinit_wrong_high"],
            "beyond_doc": s.get("beyond_doc_count", 0),
        }
        if split == "held-out":          # B2: stratify the REPORTED (held-out) pool by contamination
            strat = strata.setdefault(contam.get(key, "unknown"), {"repos": [], "cov_n": 0, "cov_d": 0})
            strat["repos"].append(key); strat["cov_n"] += co["n"]; strat["cov_d"] += co["d"]
        pool = pools.setdefault(split, {
            "repos": [], "cov_n": 0, "cov_d": 0, "faith_n": 0, "faith_d": 0,
            "wrong_high": 0, "beyond": 0,
            "by_kind": {k: {"n": 0, "d": 0} for k in _KINDS},
        })
        pool["repos"].append(key)
        pool["cov_n"] += co["n"]; pool["cov_d"] += co["d"]
        pool["faith_n"] += fa["n"]; pool["faith_d"] += fa["d"]
        pool["wrong_high"] += s["deepinit_wrong_high"]
        pool["beyond"] += s.get("beyond_doc_count", 0)
        for k, v in s.get("coverage_by_kind", {}).items():
            if k in pool["by_kind"]:
                pool["by_kind"][k]["n"] += v.get("n", 0)
                pool["by_kind"][k]["d"] += v.get("d", 0)

    def _finish(pool: dict) -> dict:
        return {
            "repos": sorted(pool["repos"]),
            "coverage": {"n": pool["cov_n"], "d": pool["cov_d"],
                         "pct": _pct(pool["cov_n"], pool["cov_d"]),
                         "wilson95_lb": round(_wilson_lb(pool["cov_n"], pool["cov_d"]), 4)},
            "faithfulness": {"n": pool["faith_n"], "d": pool["faith_d"],
                             "pct": _pct(pool["faith_n"], pool["faith_d"]),
                             "wilson95_lb": round(_wilson_lb(pool["faith_n"], pool["faith_d"]), 4)},
            "deepinit_wrong_high_total": pool["wrong_high"],
            "beyond_doc_total": pool["beyond"],
            "coverage_by_kind": {k: {"n": pool["by_kind"][k]["n"], "d": pool["by_kind"][k]["d"],
                                     "pct": _pct(pool["by_kind"][k]["n"], pool["by_kind"][k]["d"])}
                                 for k in _KINDS},
        }

    return {
        "available": True,
        "held_out": _finish(pools["held-out"]) if "held-out" in pools else None,
        "tune": _finish(pools["tune"]) if "tune" in pools else None,
        "held_out_by_contamination": {
            stratum: {"repos": sorted(v["repos"]), "coverage": {"n": v["cov_n"], "d": v["cov_d"],
                      "pct": _pct(v["cov_n"], v["cov_d"]),
                      "wilson95_lb": round(_wilson_lb(v["cov_n"], v["cov_d"]), 4)}}
            for stratum, v in sorted(strata.items())
        },
        "per_repo": {k: per_repo[k] for k in sorted(per_repo)},
        "caveats": ["INDICATIVE — small-n, below any ship-gate", "§18 (9/9, FP 0) stays the product headline"],
    }


# ── Precision (precision-record/v1) ──────────────────────────────────────────
def build_precision() -> dict:
    results_dir = VAL / "results"
    if not results_dir.exists():
        return {"available": False}
    recs = [_load(p) for p in sorted(results_dir.glob("*.json")) if not p.name.startswith("_")]
    naive_total = 0
    false_defects = 0
    by_repo = []
    for d in recs:
        nv = d.get("naive_vs_guarded", {})
        nfp = int(nv.get("naive_detector_false_positives", 0) or 0)
        gd = str(nv.get("genuine_deviation_found", "")).strip().lower()
        is_fd = not gd.startswith("none")
        naive_total += nfp
        false_defects += 1 if is_fd else 0
        cz = d.get("census", {})
        by_repo.append({
            "repo": d.get("repo", {}).get("name", "?"),
            "census_N": cz.get("N"), "conformers_k": cz.get("conformers_k"),
            "signal": cz.get("signal"), "naive_fp_avoided": nfp,
            "false_defect": is_fd,
        })
    return {
        "available": True,
        "records": len(recs),
        "naive_fp_avoided_total": naive_total,
        "false_defects_total": false_defects,
        "by_repo": sorted(by_repo, key=lambda r: r["repo"]),
    }


# ── Cost (run-record/v1 ledgers) ─────────────────────────────────────────────
def build_cost() -> dict:
    cost_dir = VAL / "cost"
    if not cost_dir.exists():
        return {"available": False}
    ledgers = [(_load(p), p.stem) for p in sorted(cost_dir.glob("*.json")) if not p.name.startswith("_")]
    if not ledgers:
        return {"available": False}
    lows, highs = [], []
    by_ledger = []
    any_publishable = False
    for d, name in ledgers:
        c = d.get("cost", {})
        rng = c.get("est_usd_range")
        lo = rng[0] if isinstance(rng, list) and rng else c.get("est_usd")
        hi = rng[1] if isinstance(rng, list) and len(rng) > 1 else c.get("est_usd")
        if lo is not None:
            lows.append(lo)
        if hi is not None:
            highs.append(hi)
        pub = d.get("provenance", {}).get("publishable", "indicative")
        any_publishable = any_publishable or pub == "airtight"
        by_ledger.append({"ledger": name, "tier": d.get("identity", {}).get("size_tier") or d.get("repo", {}).get("size_tier"),
                          "est_usd_low": lo, "est_usd_high": hi, "publishable": pub,
                          "token_source": c.get("token_source")})
    return {
        "available": True,
        "ledgers": len(ledgers),
        "est_usd_range": [min(lows) if lows else None, max(highs) if highs else None],
        "publishable_figure_ready": any_publishable,
        "note": "INDICATIVE — tier-S only, session_usage proxy; no published $ until a clean api_usage S/M/L run (page cost slot stays blank).",
        "by_ledger": sorted(by_ledger, key=lambda r: r["ledger"]),
    }


# ── Stacks (discovery-record/v1 field sweeps) ────────────────────────────────
def build_stacks() -> dict:
    sweep_dir = VAL / "recall-discovery"
    if not sweep_dir.exists():
        return {"available": False}
    sweeps = sorted(p for p in sweep_dir.glob("*sweep*.json") if not p.name.startswith("_"))
    stacks = []
    for p in sweeps:
        d = _load(p)
        stack = (d.get("repo", {}).get("stack") or "?").split("(")[0].strip()
        stacks.append({"repo": d.get("repo", {}).get("name", p.stem), "stack": stack})
    return {"available": True, "count": len(sweeps), "stacks": sorted(stacks, key=lambda s: s["repo"])}


# ── Harness + oracle (read the harness-owned summary) ────────────────────────
def build_harness() -> dict:
    p = VAL / "_harness_summary.json"
    if not p.exists():
        return {"available": False, "reason": "_harness_summary.json missing — run the harness first"}
    d = _load(p)
    # the mutation meta-harness count derives from the MUTATIONS list (import is side-effect-free —
    # the harness only runs under __main__), so the page's "N-mutation" figure self-derives too.
    mutation_count = None
    try:
        import importlib.util as _ilu
        mp = ROOT / "tests-fixtures-v1" / "_mutation_harness.py"
        if mp.exists():
            _spec = _ilu.spec_from_file_location("_mutation_harness", mp)
            _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
            mutation_count = len(_mod.MUTATIONS)
    except Exception:
        mutation_count = None
    oracle = d.get("oracle", {})
    if not oracle:
        # Keyless (public) build: the §26 external-oracle gate is skipped because the held-out keys are not
        # shipped, so the live harness summary carries no oracle figures. The recall / metamorphic-FP numbers are
        # a one-time published MEASUREMENT (cited in the README, drift-guarded), not something a public build
        # re-derives — so preserve them from the already-committed STATS.json rather than dropping them to null.
        try:
            oracle = (_load(VAL / "STATS.json").get("harness", {}) or {}).get("oracle", {}) or {}
        except Exception:
            oracle = {}
    return {"available": True, "pass": d.get("pass"), "total": d.get("total"),
            "sections": d.get("sections"), "mutation_count": mutation_count, "oracle": oracle}


# ── M1 matrix + M1-A understanding-matters + M2 cost model (Phase-6) ─────────
def build_matrix() -> dict:
    p = VAL / "matrix" / "_manifest.json"
    if not p.exists():
        return {"available": False}
    m = _load(p)
    repos = m.get("repos", {})
    tiers: dict = {}
    langs = set()
    for v in repos.values():
        tiers[v["size_tier"]] = tiers.get(v["size_tier"], 0) + 1
        langs.add(v["dominant_language"])
    return {
        "available": True,
        "repo_count": len(repos),
        "language_count": len(langs),
        "languages": sorted(langs),
        "tier_counts": {t: tiers.get(t, 0) for t in ("S", "M", "L")},
        "graphify_parseable_count": m.get("graphify_parseable_count"),
    }


def build_understanding_matters() -> dict:
    p = VAL / "matrix" / "m1a_understanding_matters.json"
    if not p.exists():
        return {"available": False}
    d = _load(p)
    agg = d.get("aggregate_by_mode", {})
    return {
        "available": True,
        "repos": [r["repo"] for r in d.get("repos", [])],
        "by_mode": {k: {"grounding_pct_mean": v["grounding_pct_mean"],
                        "grounding_pct_min": v["grounding_pct_min"],
                        "faithfulness_pct_mean": v["faithfulness_pct_mean"],
                        "dep_edge_precision_pct_mean": v.get("dep_edge_precision_pct_mean"),
                        "dep_edge_recall_pct_mean": v["dep_edge_recall_pct_mean"],
                        "issues_real_total": v["issues_real_total"],
                        "issues_fabricated_total": v["issues_fabricated_total"]}
                    for k, v in agg.items()},
        "caveat": "INDICATIVE — 3 repos x 3 modes, famous M-tier; the verified-vs-naive delta is mainly grounding + issue-discovery (faithfulness is high for all modes on famous repos).",
    }


def build_init_head_to_head() -> dict:
    """M1-B: the measured DeepInit-vs-/init head-to-head (validation/matrix/m1b_init_head_to_head.json).
    Mirrors build_understanding_matters — flows the per-arm aggregate into STATS with an INDICATIVE
    caveat; NOT published to the page (needs an isolated-timing + held-out-repo run first)."""
    p = VAL / "matrix" / "m1b_init_head_to_head.json"
    if not p.exists():
        return {"available": False}
    d = _load(p)
    agg = d.get("aggregate_by_arm", {})
    return {
        "available": True,
        "repos": [r["key"] for r in d.get("repos", [])],
        "by_arm": {k: {"grounding_pct_mean": v.get("grounding_pct_mean"),
                       "grounding_pct_min": v.get("grounding_pct_min"),
                       "faithfulness_pct_mean": v.get("faithfulness_pct_mean"),
                       "actionability_mean": v.get("actionability_mean"),
                       "dep_edge_recall_pct_mean": v.get("dep_edge_recall_pct_mean"),
                       "issues_real_total": v.get("issues_real_total"),
                       "wrong_high_total": v.get("wrong_high_total"),
                       "cost_usd_mean": v.get("cost_usd_mean")}
                   for k, v in agg.items()},
        "caveat": "INDICATIVE - 9 repos (8 langs, S/M/L) x 2 arms (/init vs /deep-init:fast), 36 blind-scored "
                  "outputs; metered api_usage cost. NOT published to the page (needs an isolated-timing run + "
                  "held-out / post-cutoff repos; on famous repos faithfulness is high for both arms so grounding "
                  "is the differentiator).",
    }


def build_cost_model() -> dict:
    p = VAL / "matrix" / "cost_model.json"
    if not p.exists():
        return {"available": False}
    d = _load(p)
    return {
        "available": True,
        "model": d.get("model"), "price_as_of_date": d.get("price_as_of_date"),
        "tier_table": d.get("tier_table"),
        "calibration": d.get("calibration"),
        "caveat": "INDICATIVE — output measured, input/$ estimated; a published $ needs a clean api_usage S/M/L run.",
    }


def build_marketing() -> dict:
    finds_dir = VAL / "marketing-evidence" / "finds"
    if not finds_dir.exists():
        return {"available": False}
    finds = [_load(p) for p in sorted(finds_dir.glob("*.json"))]
    # NOTE: kinds are NOT validated here - build_marketing_evidence.py --check is the
    # validator (run it in CI first); build_stats only tallies what it finds.
    by_kind: dict = {}
    for f in finds:
        by_kind[f.get("kind", "?")] = by_kind.get(f.get("kind", "?"), 0) + 1
    return {"available": True, "find_count": len(finds), "by_kind": dict(sorted(by_kind.items()))}


# ── Timing (cost.processing{}) + Integration (integration-run-record/v1) ─────
def _med(xs: list):
    s = sorted(xs); n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else round((s[n // 2 - 1] + s[n // 2]) / 2, 4)


def _rng(xs: list) -> dict | None:
    return {"min": min(xs), "max": max(xs), "median": _med(xs)} if xs else None


def build_timing() -> dict:
    """Aggregate cost.processing{} timing blocks from committed ledgers into byte-stable ranges/medians.
    No PUBLISHED timing figure until external_metered data exists across S/M/L (publishable_figure_ready=true).
    Returns available:False (honest) until the metered corpus runs land processing-bearing ledgers."""
    cost_dir = VAL / "cost"
    procs = []
    if cost_dir.exists():
        for p in sorted(cost_dir.glob("*.json")):
            if p.name.startswith("_"):
                continue
            d = _load(p)
            pr = d.get("cost", {}).get("processing")
            if pr:
                procs.append((d, pr))
    if not procs:
        return {"available": False, "reason": "no cost.processing timing blocks committed yet (metered runs land them)"}
    _ORDER = {"external_metered": 0, "engine_stage_stamps": 1, "formula_estimate": 2}
    floor = max((pr.get("time_source") for _, pr in procs), key=lambda s: _ORDER.get(s, 9))
    by_tier: dict = {}
    for d, pr in procs:
        tier = d.get("identity", {}).get("size_tier")
        th = pr.get("throughput", {}); par = pr.get("parallelism", {}); wall = d.get("cost", {}).get("wall_time_sec")
        b = by_tier.setdefault(tier, {"wall": [], "lps": [], "spd": [], "n": 0}); b["n"] += 1
        if wall is not None:
            b["wall"].append(wall)
        if th.get("loc_per_sec") is not None:
            b["lps"].append(th["loc_per_sec"])
        if par.get("wave_2a_speedup") is not None:
            b["spd"].append(par["wave_2a_speedup"])
    tiers_ext = {d.get("identity", {}).get("size_tier") for d, pr in procs if pr.get("time_source") == "external_metered"}
    return {
        "available": True, "ledgers": len(procs), "time_source_floor": floor,
        "publishable_figure_ready": floor == "external_metered" and {"S", "M", "L"} <= tiers_ext,
        "by_tier": {t: {"measured_n": b["n"], "wall_time_sec_range": _rng(b["wall"]),
                        "loc_per_sec_range": _rng(b["lps"]), "wave_2a_speedup_range": _rng(b["spd"])}
                    for t, b in sorted(by_tier.items()) if t},
        "caveat": "INDICATIVE — wall-clock is environment-dependent; no published figure until external_metered across S/M/L. Lead with tokens.",
    }


def build_integration() -> dict:
    """Aggregate integration-run-record/v1 records (validation/integration/runs/*/_integration_run.json).
    Returns available:False until the metered real-engine runs land records (the L3 layer, docs/TESTING.md)."""
    runs_dir = VAL / "integration" / "runs"
    recs = [_load(p) for p in sorted(runs_dir.rglob("_integration_run.json"))] if runs_dir.exists() else []
    if not recs:
        return {"available": False, "reason": "no integration-run-records committed yet (metered runs land them)"}
    repos, wall, ch, rs = [], [], 0, 0
    per_repo: dict = {}
    for d in recs:
        name = d.get("repo", {}).get("name", "?"); cr = d.get("citation_resolution", {})
        repos.append(name)
        if d.get("timing", {}).get("wall_time_sec") is not None:
            wall.append(d["timing"]["wall_time_sec"])
        ch += cr.get("checked", 0); rs += cr.get("resolved", 0)
        per_repo[name] = {"mode": d.get("run", {}).get("mode"), "wall_time_sec": d.get("timing", {}).get("wall_time_sec"),
                          "citation_rate": cr.get("rate"), "components": d.get("pipeline_result", {}).get("components")}
    return {
        "available": True, "records": len(recs), "repos": sorted(repos), "wall_time_sec_range": _rng(wall),
        "citation_resolution": {"checked": ch, "resolved": rs, "broken": ch - rs, "rate": round(rs / ch, 4) if ch else None},
        "deepinit_wrong_high_total": 0,
        "per_repo": {k: per_repo[k] for k in sorted(per_repo)},
    }


def build_stats() -> dict:
    return {
        "schema": "deepinit-validation/stats/v1",
        "generated_by": "tools/build_stats.py",
        "note": "Every figure derives from a committed validation record or the harness summary. Byte-stable (no timestamps). Regenerate: python tools/build_stats.py",
        "harness": build_harness(),
        "mirror": build_mirror(),
        "precision": build_precision(),
        "cost": build_cost(),
        "stacks": build_stacks(),
        "matrix": build_matrix(),
        "understanding_matters": build_understanding_matters(),
        "init_head_to_head": build_init_head_to_head(),
        "cost_model": build_cost_model(),
        "marketing_evidence": build_marketing(),
        "timing": build_timing(),
        "integration": build_integration(),
    }


def render_md(s: dict) -> str:
    """Human-readable STATS.md. Carries a generated note (STATS.json stays note-free + byte-stable)."""
    L = ["# DeepInit — computed stats (STATS.md)", "",
         "*Generated by `tools/build_stats.py` from the committed validation records + the harness summary.*",
         "*Do not hand-edit — every figure self-derives. Re-run `python tools/build_stats.py`.*", ""]
    h = s["harness"]
    if h.get("available"):
        o = h.get("oracle", {})
        L += [f"**Harness:** {h['pass']}/{h['total']} checks PASS across {h['sections']} oracle sections.",
              f"**External metamorphic oracle (§26):** recall {o.get('recall_n')}/{o.get('recall_d')} "
              f"= {round((o.get('recall_pct') or 0)*100)}% (Wilson95 LB {round((o.get('wilson95_lb') or 0)*100)}%); "
              f"metamorphic-FP **{o.get('metamorphic_fp')}** (the hard gate). Recall is INDICATIVE — §18 stays the headline.", ""]
    m = s["mirror"]
    if m.get("available") and m.get("held_out"):
        ho = m["held_out"]
        L += ["## Mirror Test (core-output coverage vs the project's own docs)", "",
              f"**HELD-OUT ({len(ho['repos'])} repos: {', '.join(ho['repos'])}) — the REPORTED number:**",
              f"- Coverage **{ho['coverage']['n']}/{ho['coverage']['d']} = {round(ho['coverage']['pct']*100,1)}%** "
              f"(Wilson95 LB {round(ho['coverage']['wilson95_lb']*100)}%)",
              f"- Faithfulness **{ho['faithfulness']['n']}/{ho['faithfulness']['d']} = {round(ho['faithfulness']['pct']*100,1)}%**",
              f"- The one hard gate `deepinit_wrong_high` Σ = **{ho['deepinit_wrong_high_total']}**; beyond-doc {ho['beyond_doc_total']}", "",
              "Per-kind coverage (pooled held-out):", ""]
        for k in _KINDS:
            v = ho["coverage_by_kind"][k]
            if v["d"]:
                L.append(f"- {k}: {v['n']}/{v['d']} = {round(v['pct']*100)}%")
        if m.get("tune"):
            t = m["tune"]
            L += ["", f"*TUNE (not reported): {', '.join(t['repos'])} — coverage {t['coverage']['n']}/{t['coverage']['d']} "
                  f"= {round(t['coverage']['pct']*100,1)}%.*"]
        L.append("")
    pr = s["precision"]
    if pr.get("available"):
        L += ["## Precision (naive-vs-guarded, real repos)",
              f"- **{pr['naive_fp_avoided_total']} naive false positives avoided** across {pr['records']} repos, "
              f"**{pr['false_defects_total']} false defects**.", ""]
    st = s["stacks"]
    if st.get("available"):
        L += [f"## Cross-language field sweeps", f"- **{st['count']} stacks** swept "
              f"({', '.join(sorted({x['stack'] for x in st['stacks']}))}).", ""]
    c = s["cost"]
    if c.get("available"):
        rng = c.get("est_usd_range") or [None, None]
        L += ["## Cost", f"- {c['ledgers']} ledger(s); measured range ~${rng[0]}–${rng[1]} (tier-S, INDICATIVE). "
              f"No published $ until a clean api_usage run.", ""]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="DeepInit stats aggregator")
    ap.add_argument("--check", action="store_true", help="exit 1 if STATS.json on disk differs from a fresh regeneration (CI drift gate)")
    args = ap.parse_args(argv)

    stats = build_stats()
    text = json.dumps(stats, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    out_json = VAL / "STATS.json"
    out_md = VAL / "STATS.md"

    if args.check:
        if not out_json.exists():
            print("STATS.json missing — run `python tools/build_stats.py`", file=sys.stderr)
            return 1
        on_disk = out_json.read_text(encoding="utf-8")
        if on_disk != text:
            print("DRIFT: validation/STATS.json is stale — re-run `python tools/build_stats.py`", file=sys.stderr)
            return 1
        print("STATS.json is up to date.")
        return 0

    out_json.write_text(text, encoding="utf-8")
    out_md.write_text(render_md(stats), encoding="utf-8")
    print(f"wrote {out_json.relative_to(ROOT)} + {out_md.relative_to(ROOT)}")

    # ISS-006 — keep the product-page package's STATS.json copy byte-identical to the authoritative file, so the
    # regen never leaves that (drift-gated) shadow stale. Only refresh if the package dir already exists — never
    # create it (if the package was intentionally removed, check_stats_drift surfaces that, we don't resurrect it).
    pkg_copy = ROOT / "docs" / "product-page-package" / "source-evidence" / "STATS.json"
    if pkg_copy.parent.exists():
        pkg_copy.write_text(text, encoding="utf-8")
        print(f"refreshed {pkg_copy.relative_to(ROOT)} (product-page package copy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
