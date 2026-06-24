#!/usr/bin/env python3
"""
run_integration.py — Tier-2 real-engine integration driver / monitor / snapshotter (METERED).

This is the ONLY token-spending test surface (docs/TESTING.md L3). It drives the ACTUAL deep-init
skill (a real Claude run) on a pinned corpus clone, monitors it, snapshots every emitted artifact
into the committed tree, and hands the snapshot to build_integration_record.py → an
`integration-run-record/v1` that the 0-token Tier-1 auditor (audit_integration_run.py) then re-checks.

HARD SAFETY CONTRACT (pinned by harness §A4 — a 0-token static check of this file):
  • ENV-GUARDED — exits 0 ("metered run skipped") unless DEEPINIT_REAL_ENGINE=1, so it can NEVER fire
    (or spend a token) in CI. The env flag is the single on-switch.
  • PIN & FAIL-CLOSED — checks out the pinned 40-hex SHA detached and REFUSES a dirty or
    SHA-mismatched clone (the §73 torn-tree lesson: never snapshot an ambiguous tree).
  • ROSTER SINGLE-SOURCE — only drives a repo listed in validation/integration/_manifest.json with a
    real pinned_sha; an off-roster repo is refused (no orphan run-record).
  • SEPARATION OF DUTIES — the emitted record's independent_validation.validated_by names the AUDITOR,
    never this runner. This driver records evidence; it does NOT self-attest the audit verdict.

Usage (operator / periodic — never CI):
  DEEPINIT_REAL_ENGINE=1 python tools/run_integration.py --repo helix-editor/helix \
     --sha 14eda106f0a3e6a5fc6fb5cbd96bda9774f64ae1 --clone <path/to/pinned/clone> \
     [--mode blind] [--profile aggressive] [--runs 1]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "validation" / "integration" / "_manifest.json"
SNAPSHOTS = ROOT / "validation" / "integration" / "snapshots"

# The on-switch. Absent ⇒ this runner is inert (CI-safe, 0-token). This token is load-bearing — §A4 G1.
REAL_ENGINE_ENV = "DEEPINIT_REAL_ENGINE"

# Emitted artifacts we snapshot into the committed tree (the auditor re-derives over exactly these).
SNAPSHOT_GLOBS = ("CLAUDE.md", "AGENTS.md", ".cursorrules", ".ai/**/*")


def _load_roster() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8")).get("corpus", {}) if MANIFEST.exists() else {}


def _roster_entry(repo: str) -> dict | None:
    """Find the roster entry for `repo` (by short key or full name). Off-roster ⇒ None (refused)."""
    roster = _load_roster()
    for key, entry in roster.items():
        if key == repo or entry.get("repo") == repo:
            return {"key": key, **entry}
    return None


def _git(clone: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def assert_pinned_clean(clone: Path, sha: str) -> None:
    """FAIL-CLOSED: the clone must be a git repo, checked out at EXACTLY `sha`, with a clean tree.
    Raises SystemExit otherwise (never snapshot an ambiguous/dirty/wrong-SHA tree — §73)."""
    if not (clone / ".git").exists():
        raise SystemExit(f"refuse: {clone} is not a git clone (cannot pin a SHA).")
    head = _git(clone, "rev-parse", "HEAD")
    if head != sha:
        raise SystemExit(f"refuse: clone HEAD {head[:12]} != pinned {sha[:12]} (SHA-mismatched clone — fail-closed).")
    dirty = _git(clone, "status", "--porcelain")
    if dirty:
        raise SystemExit(f"refuse: clone tree is dirty ({len(dirty.splitlines())} change(s)) — fail-closed (§73 torn-tree).")


def snapshot_artifacts(clone: Path, dest: Path) -> list[str]:
    """Copy the emitted artifacts from the run clone into the committed snapshot dir. Returns the
    relative paths copied (sorted). Removes a prior snapshot first so the set is exact, never stale."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for pattern in SNAPSHOT_GLOBS:
        for src in sorted(clone.glob(pattern)):
            if src.is_file():
                rel = src.relative_to(clone)
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest / rel)
                copied.append(rel.as_posix())
    return sorted(copied)


def drive_engine(clone: Path, entry: dict, profile: str) -> dict:
    """Drive the REAL engine (a Claude run of the skill) over the pinned clone, monitoring each stage.

    The engine is a Claude instance executing skills/deep-init/SKILL.md — there is no in-process API,
    so the metered invocation shells out to a headless `claude -p` run (the documented real-engine entry
    point). This only ever executes under DEEPINIT_REAL_ENGINE=1 (checked in main before we get here)."""
    blind = entry.get("mode") == "blind"
    prompt = (f"Run the deep-init skill on this repo at {profile} depth"
              + (" in BLIND mode (the repo's own docs are HELD OUT — do not read them)." if blind else ".")
              + " Emit the full context layer (CLAUDE.md + .ai/docs + .ai/report.html + .ai/deepinit.sarif).")
    t0 = time.perf_counter()
    started = _git(clone, "log", "-1", "--format=%cI")  # deterministic-ish stamp (no wall clock in record body)
    # The metered run. Monitored via the subprocess; a real run is minutes-to-hours (operator watches).
    proc = subprocess.run(["claude", "-p", prompt], cwd=str(clone),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    dt = round(time.perf_counter() - t0, 3)
    if proc.returncode != 0:
        raise SystemExit(f"refuse: the metered engine run failed (rc={proc.returncode}). Tail:\n{(proc.stderr or '')[-600:]}")
    return {"wall_time_sec": dt, "started": started, "finished": None,
            "stages": [], "graphify_used": (clone / ".ai" / "structural-graph.json").exists()}


def run_one(repo: str, sha: str, clone: Path, *, mode: str | None, profile: str) -> int:
    entry = _roster_entry(repo)
    if entry is None:
        raise SystemExit(f"refuse: {repo} is not in the roster ({MANIFEST.name}). Add it there first (single source of truth).")
    if entry.get("pinned_sha") != sha:
        raise SystemExit(f"refuse: --sha {sha[:12]} != roster pin {entry.get('pinned_sha','')[:12]} for {repo} (pin mismatch).")
    mode = mode or entry.get("mode", "single")
    assert_pinned_clean(clone, sha)            # FAIL-CLOSED before we spend a token
    timing = drive_engine(clone, entry, profile)
    dest = SNAPSHOTS / entry["key"]
    snapshot_artifacts(clone, dest)
    # Hand the committed snapshot to the EMITTER builder (which stamps the AUDITOR as validator).
    bir = subprocess.run([sys.executable, "tools/build_integration_record.py",
                          "--repo", repo, "--sha", sha, "--snapshot-dir", str(dest.relative_to(ROOT)),
                          "--mode", mode, "--profile", profile, "--date", time.strftime("%Y-%m-%d"),
                          "--stack", entry.get("stack", ""),
                          *(["--coverage-ref", entry["coverage_ref"]] if entry.get("coverage_ref") else [])],
                         cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(bir.stdout.strip() or bir.stderr.strip())
    return bir.returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tier-2 real-engine integration driver (METERED; env-guarded).")
    ap.add_argument("--repo", required=True, help="roster repo (short key or full owner/name)")
    ap.add_argument("--sha", required=True, help="the 40-hex pinned SHA (must match the roster)")
    ap.add_argument("--clone", required=True, help="path to the pinned, clean git clone to analyze")
    ap.add_argument("--mode", choices=["single", "multi-component", "blind"], help="override the roster mode")
    ap.add_argument("--profile", default="aggressive", choices=["fast", "thorough", "aggressive"])
    ap.add_argument("--runs", type=int, default=1, help="N stability re-runs (cost-is-no-object depth)")
    args = ap.parse_args(argv)

    # THE on-switch — without it this is inert (CI can call it freely; it spends nothing). §A4 G1.
    if os.environ.get(REAL_ENGINE_ENV) != "1":
        print(f"metered run skipped — set {REAL_ENGINE_ENV}=1 to drive the real engine (Tier-2, token-spending).")
        return 0

    clone = Path(args.clone)
    rc = 0
    for i in range(max(1, args.runs)):
        if args.runs > 1:
            print(f"── stability run {i + 1}/{args.runs} ──")
        rc = run_one(args.repo, args.sha, clone, mode=args.mode, profile=args.profile) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
