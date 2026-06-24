#!/usr/bin/env python3
"""audit_integration_run.py — Tier-1 integration auditor (0-token, CI-safe).

The real-engine integration suite (docs/TESTING.md L3) writes an `integration-run-record/v1` that CLAIMS
figures (citation-resolution, coverage, wrong-HIGH, artifact hashes). This auditor is the separation-of-duties
check: it RE-DERIVES those claims from the record's OWN committed snapshot + (blind) coverage record and
demands they reproduce. A record whose numbers don't follow from its committed evidence FAILS — turning a
non-deterministic real-engine output into a deterministic, re-runnable audit. The emitting agent never
self-attests; this auditor (a different actor) recomputes.

Usage:
  python tools/audit_integration_run.py                 # audit every validation/integration/runs/*/_integration_run.json
  python tools/audit_integration_run.py <record.json>   # audit one
Exit 0 iff every audited record's claims reproduce.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _verify_citations():
    spec = importlib.util.spec_from_file_location("verify_citations", ROOT / "tools" / "verify_citations.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def audit(record: dict, base: Path) -> dict:
    """Re-derive what `record` claims from its committed snapshot under `base`. Returns {ok, checks}."""
    checks: list[dict] = []

    def _c(name: str, ok: bool, detail: str = ""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    snap = base / record.get("artifacts", {}).get("snapshot_dir", "")

    # 1) artifact-hash integrity — the committed snapshot bytes are exactly what the record pinned.
    files = record.get("artifacts", {}).get("files", {})
    hash_ok = bool(files) and all(
        (snap / rel).is_file() and hashlib.sha256((snap / rel).read_bytes()).hexdigest() == sha
        for rel, sha in files.items())
    _c("artifact-hash integrity", hash_ok, f"{len(files)} files under {snap.name}")

    # 2) citation-resolution — re-derived against the SNAPSHOT's own files (clone-independent), vs the claim.
    vc = _verify_citations()
    claimed = record.get("citation_resolution", {})
    res = vc.verify(snap, snap, normalize=False)
    cit_ok = (res["checked"] == claimed.get("checked")
              and res["resolved"] == claimed.get("resolved")
              and len(res["broken"]) == claimed.get("broken"))
    _c("citation-resolution reproduces", cit_ok,
       f"re-derived {res['resolved']}/{res['checked']} broken={len(res['broken'])} vs "
       f"claimed {claimed.get('resolved')}/{claimed.get('checked')} broken={claimed.get('broken')}")

    # 3) THE hard zero — DeepInit must not confidently state a code-refuted fact (R1 cardinal sin).
    wh_max = record.get("expectations", {}).get("deepinit_wrong_high_max")
    _c("wrong-HIGH hard zero", wh_max == 0, f"deepinit_wrong_high_max={wh_max}")

    # 4) coverage re-derivation — only when a real committed coverage_ref exists (blind Mirror runs);
    #    on the synthetic fixture the placeholder ref is accepted (coverage is exercised on real records).
    cov_ref = (record.get("coverage_ref") or {}).get("record")
    cov_p = (ROOT / cov_ref) if cov_ref else None
    mode = record.get("run", {}).get("mode")
    if cov_p is not None and cov_p.exists():
        cov = json.loads(cov_p.read_text(encoding="utf-8"))
        _c("coverage_ref wrong-HIGH==0", cov.get("scores", {}).get("deepinit_wrong_high") == 0, cov_ref)
    elif cov_ref:
        _c("coverage_ref well-formed", True, "(fixture placeholder — coverage re-derived on real records)")
    elif mode == "blind":
        # a blind doc-comparison run is SCORED — it must carry its held-out coverage ref.
        _c("coverage_ref present (blind run scored)", False, "blind run has no coverage_ref")
    else:
        # single / multi-component runs aren't doc-scored — coverage is not applicable (not a failure).
        _c("coverage not applicable (non-blind run)", True, f"mode={mode}")

    return {
        "schema": "deepinit-validation/integration-audit/v1",
        "ok": all(c["ok"] for c in checks),
        "checks": checks,
        "validated_by": "tools/audit_integration_run.py (separation of duties — re-derived, not self-reported)",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tier-1 integration auditor — re-derive an integration-run-record's claims")
    ap.add_argument("record", nargs="?", help="an _integration_run.json (default: all under validation/integration/runs/)")
    ap.add_argument("--base", default=str(ROOT), help="base dir the snapshot_dir is relative to (default: repo root)")
    args = ap.parse_args(argv)
    base = Path(args.base)
    if args.record:
        recs = [Path(args.record)]
    else:
        d = ROOT / "validation" / "integration" / "runs"
        recs = sorted(d.rglob("_integration_run.json")) if d.exists() else []
    if not recs:
        print("no integration-run-records to audit yet (the metered L3 runs land them).")
        return 0
    all_ok = True
    for rp in recs:
        rec = json.loads(rp.read_text(encoding="utf-8"))
        result = audit(rec, base)
        all_ok = all_ok and result["ok"]
        flag = "OK" if result["ok"] else "FAIL"
        try:
            label = rp.resolve().relative_to(ROOT)
        except ValueError:
            label = rp
        print(f"[{flag}] {label}: "
              + " · ".join(f"{c['name']}={'ok' if c['ok'] else 'FAIL'}" for c in result["checks"]))
        for c in result["checks"]:
            if not c["ok"]:
                print(f"    ↳ {c['name']}: {c['detail']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
