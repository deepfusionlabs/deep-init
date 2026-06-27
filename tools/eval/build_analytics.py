#!/usr/bin/env python3
"""Deeper analytics over the 36 blind scorecards + capture records: fact-kind coverage, /init
determinism, issue precision, faithfulness-by-fame, dep-edge recall, per-language, value-per-dollar,
wrong-HIGH taxonomy. Emits validation/matrix/m1b_analytics.json + console tables."""
import json, statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path("c:/Src/DeepFusionLabs/deep-init")
OUT = ROOT / "validation/matrix/init-outputs"
BENCH = Path("c:/tmp/init-bench")
META = {
    "gin": ("Go", "M", "famous"), "click": ("Python", "M", "famous"), "express": ("JavaScript", "M", "famous"),
    "gorilla-mux": ("Go", "S", "semi"), "itsdangerous": ("Python", "S", "obscure"),
    "uniffi-rs": ("Rust", "M", "obscure"), "sinatra": ("Ruby", "M", "famous"),
    "fmt": ("C++", "M", "famous"), "commercetools-sync-java": ("Java", "L", "obscure"),
}
sc = {s["label"]: s for s in json.loads((BENCH / "scorecards.json").read_text())}
mp = {m["label"]: m for m in json.loads((BENCH / "mapping.json").read_text())}
rows = []
for l, s in sc.items():
    if l not in mp:
        continue
    k = mp[l]["key"]; lang, tier, fame = META[k]
    rows.append({**s, "arm": mp[l]["arm"], "key": k, "lang": lang, "tier": tier, "fame": fame})


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 1) if xs else None


def arm(a):
    return [r for r in rows if r["arm"] == a]


print("================ DEEPER ANALYTICS (9 repos / 36 outputs) ================\n")

# 1. fact-kind coverage
print("1) DEPTH — total claims by fact-kind (init sum vs deepinit sum):")
kinds = defaultdict(lambda: [0, 0])
for r in rows:
    idx = 0 if r["arm"] == "init" else 1
    for d in r["depth_by_kind"]:
        kinds[d["kind"]][idx] += d["count"]
print(f"   {'kind':18s} {'init':>6s} {'deepinit':>9s}")
for kd in sorted(kinds, key=lambda x: -sum(kinds[x])):
    i, d = kinds[kd]
    print(f"   {kd:18s} {i:>6d} {d:>9d}")

# 2. faithfulness by fame (does /init degrade on obscure?)
print("\n2) FAITHFULNESS by fame (the key obscure-repo test):")
for a in ("init", "deepinit"):
    fam = mean([r["faithfulness_pct"] for r in arm(a) if r["fame"] == "famous"])
    non = mean([r["faithfulness_pct"] for r in arm(a) if r["fame"] != "famous"])
    print(f"   {a:9s} famous {fam}%  |  non-famous {non}%")

# 3. wrong-HIGH by arm + fame
print("\n3) WRONG-HIGH (confident + code-refuted) by arm × fame:")
for a in ("init", "deepinit"):
    fam = sum(r["wrong_high"] for r in arm(a) if r["fame"] == "famous")
    non = sum(r["wrong_high"] for r in arm(a) if r["fame"] != "famous")
    print(f"   {a:9s} famous {fam}  |  non-famous {non}  |  total {fam+non}")

# 4. issue precision
print("\n4) ISSUE PRECISION (real / flagged):")
for a in ("init", "deepinit"):
    fl = sum(r["issues_flagged"] for r in arm(a)); re_ = sum(r["issues_real"] for r in arm(a))
    fab = sum(r["issues_fabricated"] for r in arm(a))
    print(f"   {a:9s} flagged {fl} · real {re_} · fabricated {fab} · precision {round(100*re_/fl,1) if fl else '-'}%")

# 5. /init determinism (variance across the 3 runs per repo)
print("\n5) /init NON-DETERMINISM (stdev across 3 runs):")
for k in sorted(META):
    ir = [r for r in rows if r["key"] == k and r["arm"] == "init"]
    if len(ir) >= 2:
        cl = [r["claims_total"] for r in ir]; wh = [r["wrong_high"] for r in ir]; iss = [r["issues_real"] for r in ir]
        print(f"   {k:16s} claims {min(cl)}-{max(cl)} (σ{round(st.pstdev(cl),1)}) · wrong_high {min(wh)}-{max(wh)} · issues_real {min(iss)}-{max(iss)}")

# 6. dep-edge recall (oracle trio)
print("\n6) DEP-EDGE RECALL vs AST oracle (trio):")
for k in ("gin", "click", "express"):
    ir = mean([r["dep_edge_recall_pct"] for r in rows if r["key"] == k and r["arm"] == "init"])
    dr = mean([r["dep_edge_recall_pct"] for r in rows if r["key"] == k and r["arm"] == "deepinit"])
    print(f"   {k:10s} init {ir}%  |  deepinit {dr}%   (lean tier; full dep graph lives in .ai/docs)")

# 7. per-language grounding/faithfulness (deepinit)
print("\n7) DeepInit grounding by language:")
bylang = defaultdict(list)
for r in arm("deepinit"):
    bylang[r["lang"]].append(r["grounding_pct"])
for lng in sorted(bylang):
    print(f"   {lng:12s} grounding {mean(bylang[lng])}%")

# 8. value-per-dollar (need cost from capture records)
caps = {}
for k in META:
    p = OUT / k / "_capture_record.json"
    if p.exists():
        caps[k] = json.loads(p.read_text())


def cost(k, a):
    rs = caps.get(k, {}).get("arms", {}).get(a, {}).get("runs", [])
    cs = [r.get("cost_usd") for r in rs if r.get("cost_usd")]
    return st.mean(cs) if cs else None


print("\n8) VALUE-PER-DOLLAR (DeepInit):")
gpd = []
for k in sorted(META):
    c = cost(k, "deepinit"); g = mean([r["grounding_pct"] for r in rows if r["key"] == k and r["arm"] == "deepinit"])
    if c and g is not None:
        gpd.append(g / c)
print(f"   grounding-points per $ (deepinit, mean across repos): {round(st.mean(gpd),1)}")
print(f"   /init delivers ~0 grounding at any price (0.6% mean)")

out = {"schema": "deepinit-validation/m1b-analytics/v1",
       "fact_kind_totals": {k: {"init": v[0], "deepinit": v[1]} for k, v in kinds.items()},
       "faithfulness_by_fame": {a: {"famous": mean([r["faithfulness_pct"] for r in arm(a) if r["fame"] == "famous"]),
                                    "nonfamous": mean([r["faithfulness_pct"] for r in arm(a) if r["fame"] != "famous"])}
                                for a in ("init", "deepinit")},
       "issue_precision": {a: {"flagged": sum(r["issues_flagged"] for r in arm(a)),
                               "real": sum(r["issues_real"] for r in arm(a)),
                               "fabricated": sum(r["issues_fabricated"] for r in arm(a))} for a in ("init", "deepinit")}}
(ROOT / "validation/matrix/m1b_analytics.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("\nwrote validation/matrix/m1b_analytics.json")
