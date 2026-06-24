#!/usr/bin/env python3
"""
build_integration_record.py — assemble a `deepinit-validation/integration-run-record/v1`
from a completed real-engine (Tier-2) run's committed snapshot.

This is the EMITTER side of the integration framework. It records what a run produced; it
deliberately does NOT self-attest the audit verdict — `independent_validation.validated_by`
names `tools/audit_integration_run.py` (a DIFFERENT actor), which re-derives every claim from
the same committed snapshot (separation of duties). The deterministic parts this builder fills
(artifact sha256s, citation-resolution counts) are exactly what the auditor re-computes and
demands reproduce — so a tampered record FAILS the §84 auditor.

It extends the `build_mirror_record.py` lineage (same ROOT, same binary-LF stability discipline);
the coverage scoring stays in build_mirror_record (referenced here by `coverage_ref`, not restated).

Usage (called by tools/run_integration.py after a metered run; never fires in CI):
  python tools/build_integration_record.py --repo helix-editor/helix --sha <40-hex> \
     --snapshot-dir validation/integration/snapshots/helix --mode blind --profile aggressive \
     --model claude-opus-4-8 --date 2026-06-20 [--timing <run_timing.json>] \
     [--cost-ref validation/cost/helix.json] [--coverage-ref validation/coverage/results/helix.json]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The auditor that re-derives this record's claims — the SEPARATION-OF-DUTIES validator. The emitter
# (this builder) records evidence; it never grades itself. The auditor (a different actor) recomputes.
AUDITOR = "tools/audit_integration_run.py (separation of duties — NOT the emitting agent)"

_CAVEATS = [
    "INDICATIVE — small-n, fuzzy truth, below any ship-gate",
    "attribution-adjudicated — divergences resolved to CODE, not auto-scored",
    "doc-bounded — agreement with a good human doc, not absolute completeness",
    "§18 (9/9, FP 0) stays the product headline",
]

_STAGES = ("detect", "plan", "extract", "review", "adr_kl", "issue_detect", "issue_raise",
           "filter", "redact", "verify", "emit", "horizontal", "report")


def _verify_citations():
    spec = importlib.util.spec_from_file_location("verify_citations", ROOT / "tools" / "verify_citations.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _hash_tree(snapshot_dir: Path) -> dict:
    """sha256 of every file under the snapshot (binary, repo-relative key, sorted) — the
    byte-stability anchor the auditor re-derives."""
    files = {}
    for p in sorted(snapshot_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(snapshot_dir).as_posix()
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return files


def build_record(repo: str, sha: str, snapshot_dir: Path, *, mode: str, profile: str,
                 model: str, date: str, stack: str = "", timing: dict | None = None,
                 cost_ref: str | None = None, coverage_ref: str | None = None,
                 expectations: dict | None = None) -> dict:
    """Assemble the integration-run-record/v1 from a completed run's committed snapshot.

    Pure given the on-disk snapshot (no clock, no RNG): the citation-resolution + artifact hashes
    are re-derived from the snapshot, so the record reproduces byte-stably and the auditor can
    re-check it. The blind doc-comparison coverage stays in `coverage_ref` (build_mirror_record)."""
    snapshot_dir = Path(snapshot_dir)
    files = _hash_tree(snapshot_dir)

    vc = _verify_citations()
    res = vc.verify(snapshot_dir, snapshot_dir, normalize=False)
    checked, resolved, broken = res["checked"], res["resolved"], len(res["broken"])

    timing = timing or {}
    stages = timing.get("stages", [])
    wall = timing.get("wall_time_sec", round(sum(s.get("dt_sec", 0.0) for s in stages), 3))

    exp = dict(expectations or {})
    exp.setdefault("coverage_floor_wilson95_lb", 0.20)
    exp.setdefault("faithfulness_floor", 0.90)
    exp.setdefault("citation_resolution_floor", 1.0)
    exp["deepinit_wrong_high_max"] = 0  # the cardinal-sin hard zero is NOT operator-tunable
    exp.setdefault("components_min", 1)

    record = {
        "schema": "deepinit-validation/integration-run-record/v1",
        "program": "Real-engine integration suite",
        "repo": {"name": repo, "pinned_sha": sha, "stack": stack,
                 "source_files": sum(1 for r in files if not r.startswith(".ai/"))},
        "run": {"mode": mode, "profile": profile, "model": model, "date": date,
                "engine": "deep-init skill (a Claude instance executing skills/deep-init/SKILL.md)",
                "graphify_used": bool(timing.get("graphify_used", False))},
        "timing": {"wall_time_sec": wall,
                   "started": timing.get("started"), "finished": timing.get("finished")},
        "stages": stages,
        "artifacts": {
            "snapshot_dir": snapshot_dir.relative_to(ROOT).as_posix() if snapshot_dir.is_relative_to(ROOT) else str(snapshot_dir),
            "hashes_file": None,
            "files": files,
            "manifest_present": (snapshot_dir / ".ai" / "manifest.json").is_file(),
        },
        "pipeline_result": {
            "components": timing.get("components"),
            "verification_checked": resolved + broken,
            "verification_resolved": resolved,
            "verification_refuted": broken,
            "issues_fired": timing.get("issues_fired", 0),
            "suppressions_named": timing.get("suppressions_named", 0),
        },
        "citation_resolution": {
            "checked": checked, "resolved": resolved, "broken": broken,
            "rate": round(resolved / checked, 4) if checked else 1.0,
            "shifting_warned": len(res.get("shifting_line_cites", []) or []),
            "source": "tools/verify_citations.verify",
        },
        "independent_validation": {
            # The EMITTER stamps WHO validates — not the verdict. The auditor (a different actor)
            # fills/checks the booleans below by re-derivation; the emitter never self-grades them.
            "validated_by": AUDITOR,
        },
        "cost_ref": {"ledger": cost_ref, "harness_section": "§33"} if cost_ref else None,
        "coverage_ref": {"record": coverage_ref, "harness_section": "§34"} if coverage_ref else None,
        "expectations": exp,
        "provenance": {
            "doc_in_inputs": (mode != "blind"),
            "key_held_out": (mode == "blind"),
            "publishable": "indicative" if mode == "blind" else "internal-only",
            "harness_section": "§77",
            "caveats": _CAVEATS,
        },
    }
    return record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Assemble an integration-run-record/v1 from a committed snapshot.")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument("--mode", default="single", choices=["single", "multi-component", "blind"])
    ap.add_argument("--profile", default="thorough", choices=["fast", "thorough", "aggressive"])
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--date", required=True)
    ap.add_argument("--stack", default="")
    ap.add_argument("--timing", help="optional run-timing JSON ({wall_time_sec, stages:[...], ...})")
    ap.add_argument("--cost-ref")
    ap.add_argument("--coverage-ref")
    ap.add_argument("--out", help="output path (default validation/integration/runs/<repo-leaf>/_integration_run.json)")
    args = ap.parse_args(argv)

    timing = json.loads(Path(args.timing).read_text(encoding="utf-8")) if args.timing else {}
    rec = build_record(args.repo, args.sha, Path(args.snapshot_dir), mode=args.mode, profile=args.profile,
                        model=args.model, date=args.date, stack=args.stack, timing=timing,
                        cost_ref=args.cost_ref, coverage_ref=args.coverage_ref)
    leaf = args.repo.split("/")[-1]
    out = Path(args.out) if args.out else (ROOT / "validation" / "integration" / "runs" / leaf / "_integration_run.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    label = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"wrote {label}  (citations {rec['citation_resolution']['resolved']}/"
          f"{rec['citation_resolution']['checked']}, {len(rec['artifacts']['files'])} files, validated_by the auditor)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
