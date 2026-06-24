#!/usr/bin/env python3
"""public_harness.py — prove the validation suite is GREEN without the internal held-out keys (M8-T7 / M8-P1).

The public OSS repo must NOT ship the held-out oracle keys (PUBLICATION-BOUNDARY.md `internal`): shipping
`tests-fixtures-v1/_external/_external_keys.json` or `validation/coverage/_reference_keys/*` would contaminate
the very anti-overfit firewall they protect. So a real coupling exists: does the harness still run GREEN when
those files are ABSENT (as they will be in the public checkout)?

This runner answers it deterministically + SAFELY, with NO filesystem mutation: it runs the full harness with
DEEPINIT_PUBLIC_HARNESS=1, which makes the suite treat the internal-only held-out keys as ABSENT (emulating a
public checkout) — so the key-dependent oracles degrade to their internal-only inert-skip path. No committed
file is renamed or deleted, so two concurrent runs (or a CI matrix) can never race or leave a dirty tree.

Exit 0 iff the harness is green in public mode AND the §26 oracle degraded to its internal-only path.

Usage:  PYTHONUTF8=1 python tools/public_harness.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
HARNESS = PKG / "tests-fixtures-v1" / "_chat_validation.py"


def _run_harness(env_extra: dict) -> tuple[int, str]:
    env = {**os.environ, "PYTHONUTF8": "1", **env_extra}
    p = subprocess.run([sys.executable, str(HARNESS)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    print("══ public-harness check — is the suite green WITHOUT the internal held-out keys? ══\n")

    # baseline: the internal harness must be green first (with the keys present)
    rc0, out0 = _run_harness({})
    if rc0 != 0:
        print("BASELINE NOT GREEN (with keys present) — fix the suite first. Last lines:")
        print("\n".join(out0.strip().splitlines()[-4:]))
        return 2
    base_result = next((l for l in out0.splitlines() if "RESULT:" in l), "?").strip()
    print(f"baseline (keys present): GREEN — {base_result}\n")

    # public mode: the suite treats the internal-only held-out keys as ABSENT (no file is moved)
    rc, out = _run_harness({"DEEPINIT_PUBLIC_HARNESS": "1"})
    result = next((l for l in out.splitlines() if "RESULT:" in l), "?").strip()
    green = rc == 0
    # the §26 oracle must have degraded to its internal-only inert-skip (not silently dropped, not crashed)
    degraded = "INTERNAL-ONLY (held-out key not shipped publicly" in out

    print(f"public run (keys treated absent): {'GREEN' if green else 'RED'} — {result}")
    print(f"§26 degraded to internal-only: {degraded}")

    # The public-mode run REWROTE validation/_harness_summary.json at the REDUCED count (no oracle data).
    # Re-run the harness in NORMAL mode once so the summary on disk reflects the canonical internal count
    # (build_stats / the drift guard read it). Same pattern as the mutation harness's end-of-run restore.
    _run_harness({})

    ok = green and degraded
    print("\n" + "═" * 52)
    print(f"  RESULT: {'PUBLIC HARNESS GREEN — the suite passes without the internal held-out keys' if ok else 'ACTION NEEDED — the public harness is not green without the keys'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
