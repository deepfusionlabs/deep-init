#!/usr/bin/env python3
"""Extract the full instrumentation picture from the metered capture (cost, tokens, output footprint,
wall-clock) by repo + size tier, for both arms. Cost+tokens are concurrency-independent (clean, real
total_cost_usd from --output-format json); wall-clock is parsed from logs and CAVEATED (parallel groups)."""
import json, re, glob
from pathlib import Path

ROOT = Path("c:/Src/DeepFusionLabs/deep-init")
OUT = ROOT / "validation/matrix/init-outputs"
MAN = json.loads((ROOT / "validation/matrix/_manifest.json").read_text())["repos"]
BENCH = Path("c:/tmp/init-bench")

# manifest key may differ from our capture key
KEYMAP = {"commercetools-sync-java": "commercetools-sync-java"}


def man(key):
    k = KEYMAP.get(key, key)
    m = MAN.get(k, {})
    return m.get("source_loc"), m.get("size_tier"), m.get("file_count")


def runs(cap, arm):
    return cap.get("arms", {}).get(arm, {}).get("runs", [])


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


# wall-clock per repo from logs (caveat: parallel contention)
durs = {}
for lg in glob.glob(str(BENCH / "capture-*.log")):
    txt = Path(lg).read_text(encoding="utf-8", errors="replace")
    starts, dones = {}, {}
    for m in re.finditer(r"\[(\d\d):(\d\d):(\d\d)\] \[\w\] capture (\S+) ", txt):
        starts[m.group(4)] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    for m in re.finditer(r"\[(\d\d):(\d\d):(\d\d)\] \[\w\] done (\S+)", txt):
        dones[m.group(4)] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    for k in starts:
        if k in dones:
            d = dones[k] - starts[k]
            if d < 0:
                d += 86400  # midnight wrap
            durs[k] = d

rows = []
for key_dir in sorted(OUT.iterdir()):
    key = key_dir.name
    if key.startswith("_"):
        continue
    cap_p = key_dir / "_capture_record.json"
    if not cap_p.exists():
        continue
    cap = json.loads(cap_p.read_text())
    loc, tier, fc = man(key)
    row = {"key": key, "loc": loc, "tier": tier, "files": fc, "wall_sec_total": durs.get(key)}
    for arm in ("init", "deepinit"):
        rs = runs(cap, arm)
        if not rs:
            continue
        row[f"{arm}_cost"] = mean([r.get("cost_usd") for r in rs])
        row[f"{arm}_otok"] = mean([(r.get("usage") or {}).get("output_tokens") for r in rs])
        row[f"{arm}_itok"] = mean([(r.get("usage") or {}).get("input_tokens") for r in rs])
        # output footprint
        md = key_dir / arm / "run-1" / "CLAUDE.md"
        row[f"{arm}_md_bytes"] = md.stat().st_size if md.exists() else None
        if arm == "deepinit":
            aidir = key_dir / "deepinit" / "run-1" / ".ai"
            row["deep_ai_docs"] = len(list(aidir.rglob("*.md"))) if aidir.exists() else 0
    rows.append(row)

print(f"{'repo':16s} {'tier':4s} {'loc':>7s} | {'init $':>7s} {'init otok':>9s} | {'deep $':>7s} {'deep otok':>9s} {'deep docs':>9s} | {'mult':>5s} | {'wall(s)*':>8s}")
for r in rows:
    mult = round(r.get("deepinit_cost") / r["init_cost"], 1) if r.get("deepinit_cost") and r.get("init_cost") else None
    print(f"{r['key']:16s} {str(r['tier']):4s} {str(r['loc']):>7s} | "
          f"{r.get('init_cost','-'):>7} {str(r.get('init_otok','-')):>9} | "
          f"{r.get('deepinit_cost','-'):>7} {str(r.get('deepinit_otok','-')):>9} {str(r.get('deep_ai_docs','-')):>9} | "
          f"{str(mult):>5} | {str(r.get('wall_sec_total','-')):>8}")

# by tier
print("\n=== by size tier (mean) ===")
for tier in ("S", "M", "L"):
    tr = [r for r in rows if r["tier"] == tier]
    if not tr:
        continue
    ic = mean([r.get("init_cost") for r in tr]); dc = mean([r.get("deepinit_cost") for r in tr])
    io = mean([r.get("init_otok") for r in tr]); do = mean([r.get("deepinit_otok") for r in tr])
    loc = mean([r["loc"] for r in tr])
    print(f"  {tier} (n={len(tr)}, ~{int(loc) if loc else '?'} loc): init ${ic} / {io} otok · deepinit ${dc} / {do} otok · mult {round(dc/ic,1) if ic and dc else '?'}x")

# cost per 1k loc
print("\n=== cost efficiency ($ per 1k source-loc) ===")
for r in rows:
    if r["loc"] and r.get("deepinit_cost"):
        print(f"  {r['key']:16s} ({r['tier']}, {r['loc']:>6} loc): init ${round(1000*r['init_cost']/r['loc'],3)} · deepinit ${round(1000*r['deepinit_cost']/r['loc'],3)} per 1k loc")

out = {"schema": "deepinit-validation/m1b-instrumentation/v1",
       "note": "Real total_cost_usd (api_usage-grade) + tokens per arm/run; wall_sec is CONTENDED (parallel groups) — indicative only.",
       "by_repo": rows}
(ROOT / "validation/matrix/m1b_instrumentation.json").write_text(
    json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("\nwrote validation/matrix/m1b_instrumentation.json")
