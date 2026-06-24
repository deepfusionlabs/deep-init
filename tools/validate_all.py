#!/usr/bin/env python3
"""validate_all.py — one command, every gate (M8-T10 / M8-A1).

Runs the full DeepInit validation surface in sequence and reports a single consolidated result:

  1. the deterministic harness           tests-fixtures-v1/_chat_validation.py   (all-PASS)
  2. the stats aggregator drift gate      tools/build_stats.py --check            (STATS.json current)
  3. the count-drift guard                tools/check_stats_drift.py              (page/README figures match)
  4. the mutation meta-harness            tests-fixtures-v1/_mutation_harness.py  (every check load-bearing)
  5. the public-harness contract          tools/public_harness.py                 (green without internal keys)

Automation > a manual step (objective hierarchy #2): one entry point for the dev loop, `make validate`,
and CI. Exit 0 iff EVERY gate passes; the first failing gate's tail is printed for triage.

Usage:  PYTHONUTF8=1 python tools/validate_all.py
        PYTHONUTF8=1 python tools/validate_all.py --fast   # skip the public-harness re-run (steps 1-4 only)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent

STEPS = [
    ("deterministic harness", [sys.executable, "tests-fixtures-v1/_chat_validation.py"], False),
    ("stats aggregator drift gate", [sys.executable, "tools/build_stats.py", "--check"], False),
    ("count-drift guard", [sys.executable, "tools/check_stats_drift.py"], False),
    ("integration auditor (Tier-1 re-derivation)", [sys.executable, "tools/audit_integration_run.py"], False),
    ("mutation meta-harness", [sys.executable, "tests-fixtures-v1/_mutation_harness.py"], False),
    ("public-harness contract", [sys.executable, "tools/public_harness.py"], True),  # True = skipped by --fast
]


def _run(cmd: list[str]) -> tuple[int, str]:
    env = {**os.environ, "PYTHONUTF8": "1"}
    p = subprocess.run(cmd, cwd=str(PKG), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    fast = "--fast" in argv
    print("══ validate_all — running every DeepInit gate ══\n")
    results = []
    for name, cmd, skip_fast in STEPS:
        if fast and skip_fast:
            print(f"  [SKIP] {name} (--fast)")
            continue
        t0 = time.perf_counter()
        rc, out = _run(cmd)
        dt = time.perf_counter() - t0
        result_line = next((l.strip() for l in reversed(out.splitlines()) if "RESULT:" in l), "")
        ok = rc == 0
        results.append((name, ok))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  ({dt:.1f}s)  {result_line}")
        if not ok:
            print("        ── failing gate tail ──")
            for line in out.strip().splitlines()[-12:]:
                print(f"        {line}")

    n_pass = sum(1 for _, ok in results if ok)
    print("\n" + "═" * 56)
    all_ok = n_pass == len(results)
    print(f"  RESULT: {n_pass}/{len(results)} gates passed"
          + ("" if all_ok else " — VALIDATION FAILED"))
    if all_ok:
        print("  ✓ all gates green — the validation surface is intact")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
