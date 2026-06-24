#!/usr/bin/env python3
"""build_marketing_evidence.py — compile the marketing-evidence finds into a browsable ledger.

Globs `validation/marketing-evidence/finds/*.json` (`marketing-find/v1`), validates each against the
discipline (grounded + re-derivable + GATED-framed + asset-tagged), and writes
`validation/marketing-evidence/findings.md` grouped by target asset and by kind. Byte-stable
(sorted, no timestamps) so it can be drift-guarded.

Phase 6 GATHERS; Phase 7 ASSEMBLES the page/README by SELECTING from findings.md.

Usage:
  python tools/build_marketing_evidence.py            # write findings.md
  python tools/build_marketing_evidence.py --check     # exit 1 if findings.md is stale OR any find invalid
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ME = ROOT / "validation" / "marketing-evidence"
FINDS = ME / "finds"
OUT = ME / "findings.md"

KINDS = {"smart-finding", "comprehension-win", "statistic", "mirror-demo",
         "understanding-matters", "cross-language", "cost-time", "depth-scale"}
REQUIRED = {"id", "kind", "headline", "detail", "gated_framing", "target_asset",
            "source_record", "date"}


def validate(find: dict, name: str) -> list[str]:
    errs = []
    missing = REQUIRED - set(find)
    if missing:
        errs.append(f"{name}: missing fields {sorted(missing)}")
    if find.get("kind") not in KINDS:
        errs.append(f"{name}: bad kind {find.get('kind')!r}")
    if not find.get("source_record"):
        errs.append(f"{name}: no source_record (re-derivability discipline)")
    ta = find.get("target_asset")
    if not isinstance(ta, list) or not ta:
        errs.append(f"{name}: target_asset must be a non-empty list")
    # the inherently-local kinds (a specific code location) MUST carry file:line grounding or a repo;
    # the aggregate kinds (a pooled stat / cross-language story / A/B delta) anchor on source_record.
    LOCAL = {"smart-finding", "comprehension-win"}
    grounded = bool(find.get("grounding")) or bool(find.get("repo"))
    if not grounded and find.get("kind") in LOCAL:
        errs.append(f"{name}: a {find['kind']} must be grounded to a file:line or a repo")
    return errs


def load_finds() -> tuple[list[dict], list[str]]:
    finds, errs = [], []
    if not FINDS.exists():
        return finds, errs
    for p in sorted(FINDS.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            errs.append(f"{p.name}: unreadable ({e})")
            continue
        errs += validate(d, p.name)
        finds.append(d)
    return finds, errs


def render(finds: list[dict]) -> str:
    L = ["# DeepInit — marketing-evidence ledger (`findings.md`)", "",
         "*Compiled by `tools/build_marketing_evidence.py` from `finds/*.json`. Do not hand-edit.*",
         "*GATHERED during Phase-6 maturation; Phase 7 ASSEMBLES the page/README by selecting from here.*",
         "*Every find is GATED-framed (comprehension, never \"bugs in famous repos\"), grounded, re-derivable.*",
         "", f"**{len(finds)} finds.**", ""]
    # by target asset
    by_asset: dict[str, list[dict]] = {}
    for f in finds:
        for a in f.get("target_asset", []):
            by_asset.setdefault(a, []).append(f)
    L += ["## By target asset (Phase-7 selection view)", ""]
    for asset in sorted(by_asset):
        L.append(f"### `{asset}`")
        for f in sorted(by_asset[asset], key=lambda x: x["id"]):
            ind = " *(indicative)*" if f.get("indicative") else ""
            L.append(f"- **{f['id']}** [{f['kind']}]{ind} — {f['headline']}")
        L.append("")
    # full detail by id
    L += ["## All finds (detail)", ""]
    for f in sorted(finds, key=lambda x: x["id"]):
        ind = " *(INDICATIVE)*" if f.get("indicative") else ""
        L.append(f"### {f['id']} — {f['headline']}{ind}")
        L.append(f"*{f['kind']}* · assets: {', '.join('`'+a+'`' for a in f.get('target_asset', []))}")
        if f.get("repo"):
            sha = (f.get("commit") or "")[:12]
            L.append(f"· repo: `{f['repo']}{('@'+sha) if sha else ''}`")
        L.append("")
        L.append(f["detail"])
        if f.get("stat"):
            L.append(f"\n> **stat:** `{json.dumps(f['stat'], ensure_ascii=False)}`")
        if f.get("grounding"):
            L.append("\n**Grounding:**")
            for g in f["grounding"]:
                ln = f":{g['line']}" if g.get("line") else ""
                L.append(f"- `{g.get('file','')}{ln}` — {g.get('note','')}")
        L.append(f"\n*GATED framing:* {f['gated_framing']}")
        L.append(f"\n*Source record:* `{f['source_record']}`")
        L.append("")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if not ME.exists():
        # the marketing-evidence corpus is internal/website material — not shipped in a public release;
        # nothing to compile or check here.
        print("marketing-evidence corpus not present — skipping (not shipped in this repo).")
        return 0
    finds, errs = load_finds()
    if errs:
        print("MARKETING-EVIDENCE VALIDATION ERRORS:", file=sys.stderr)
        for e in errs:
            print("  " + e, file=sys.stderr)
        return 1
    text = render(finds)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("DRIFT: findings.md is stale — re-run build_marketing_evidence.py", file=sys.stderr)
            return 1
        print(f"findings.md up to date ({len(finds)} finds).")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(finds)} finds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
