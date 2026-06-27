#!/usr/bin/env python3
"""
run_init_benchmark.py — METERED Stage-1 capture for the DeepInit-vs-`/init` head-to-head.

Captures the RAW output of BOTH arms — Claude Code's built-in `/init` and the DeepInit skill —
on the SAME pinned clone, K runs each, into the committed evidence tree, plus each run's real
measured cost (`claude --output-format json` → total_cost_usd). It CAPTURES ONLY. Blind scoring
(grounding / faithfulness / dep-edge recall vs the AST oracle) is Stage 2 (independent verifier
agents, separation of duties); the m1b record + STATS/harness wiring is Stage 3-4. (R1: every
number we later publish must trace back to a raw CLAUDE.md committed here.)

HARD SAFETY CONTRACT (mirrors tools/run_integration.py + harness §85):
  • ENV-GUARDED  — inert (exit 0, spends nothing) unless DEEPINIT_REAL_ENGINE=1. The single on-switch.
  • PIN & FAIL-CLOSED — refuses a dirty / SHA-mismatched clone before spending a token (§73 torn-tree).
  • BUDGET-CAPPED — every metered `claude` call passes --max-budget-usd as a hard per-run spend ceiling.
  • CAPTURE-ONLY / SEPARATION OF DUTIES — records raw outputs + cost; it does NOT score (Stage 2 does).

THE OPEN RISK (run --probe FIRST): whether the built-in `/init` command executes under `-p`
(headless) is NOT guaranteed — built-in commands that open an interactive dialog do not run in
-p mode, and `/init` is undocumented there. `--probe` runs ONE cheap `/init` on a throwaway clone
and reports whether a CLAUDE.md was emitted, so we confirm the capture path before the full matrix.
If the probe fails, fall back to interactive capture (documented in the runbook) — do NOT fabricate.

NOTE on auth: do NOT use --bare for a subscription/OAuth login — under --bare auth is strictly
ANTHROPIC_API_KEY/apiKeyHelper (OAuth + keychain are never read), so a normal (non-bare) session is
the default here; both arms run identically so the comparison stays fair.

Usage (operator only — never CI):
  # Stage-0 cheap probe (~one small run): does headless /init emit a CLAUDE.md here?
  DEEPINIT_REAL_ENGINE=1 python tools/run_init_benchmark.py --probe --clone /path/to/throwaway-clone

  # Full capture for one repo (K runs of each arm), into validation/matrix/init-outputs/<key>/:
  DEEPINIT_REAL_ENGINE=1 python tools/run_init_benchmark.py \
     --repo gin-gonic/gin --sha d75fcd4c9ab2... --clone /path/to/pinned/clone --runs 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_ROOT = ROOT / "validation" / "matrix" / "init-outputs"

# The single on-switch. Absent ⇒ this runner is inert (CI-safe, 0-token). Load-bearing (gated in Stage 4).
REAL_ENGINE_ENV = "DEEPINIT_REAL_ENGINE"

# Resolve the executables to a full path (Windows: `claude` is a .CMD shim that bare-name CreateProcess
# can't find — shutil.which honours PATHEXT and returns the real path).
_CLAUDE = shutil.which("claude") or "claude"
_GIT = shutil.which("git") or "git"

# The two arms — BOTH invoked as explicit slash commands (the deep-init skill sets
# `disable-model-invocation: true`, so a natural-language prompt does NOT trigger it; it must be a
# user slash invocation, which is exactly what works in headless `-p` mode). /deep-init:fast runs the
# COMPLETE grounded pipeline (two-tier CLAUDE.md + .ai/docs + report-only issues) with only the review
# cycles reduced — a faithful, conservative DeepInit arm (full mode would score ≥ this). Both arms
# write a lean CLAUDE.md at the repo root, the comparable always-loaded front-door file.
INIT_PROMPT = "/init"
DEEPINIT_PROMPT = ("/deep-init:fast Run non-interactively on THIS repository: use sensible defaults, "
                   "do not ask questions, emit the full context layer (CLAUDE.md + .ai/docs).")


def _git(clone: Path, *args: str) -> str:
    return subprocess.run([_GIT, "-C", str(clone), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def assert_pinned_clean(clone: Path, sha: str) -> None:
    """FAIL-CLOSED: the clone must be a git repo, checked out at EXACTLY `sha`, with a clean tree.
    `sha` may be an abbreviation (the m1a record pins 12-hex) — it is resolved to a full SHA via
    `git rev-parse` and compared to the full HEAD, so the check is strict but abbreviation-tolerant."""
    if not (clone / ".git").exists():
        raise SystemExit(f"refuse: {clone} is not a git clone (cannot pin a SHA).")
    head = _git(clone, "rev-parse", "HEAD")               # full 40-hex
    want = _git(clone, "rev-parse", sha)                   # resolve abbrev/ref → full ('' if unknown)
    if not want or head != want:
        raise SystemExit(f"refuse: clone HEAD {head[:12]} != pinned {sha} (SHA-mismatched clone — fail-closed).")
    dirty = _git(clone, "status", "--porcelain")
    if dirty:
        raise SystemExit(f"refuse: clone tree is dirty ({len(dirty.splitlines())} change(s)) — fail-closed (§73 torn-tree).")


def _reset_pristine(clone: Path) -> None:
    """Restore the clone to its pristine pinned tree between runs (discard writes + remove untracked)."""
    _git(clone, "checkout", "--", ".")
    _git(clone, "clean", "-fdq")


def _claude_version() -> str:
    return subprocess.run([_CLAUDE, "--version"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def run_arm(clone: Path, prompt: str, *, model: str, budget: float, plugin_dir: str | None = None) -> dict:
    """One metered arm run: drive `claude -p`, capture the emitted CLAUDE.md + the run's real cost.

    The clone is mutated (the arm writes CLAUDE.md); the caller resets it pristine between runs, so
    the clone MUST be a throwaway pinned clone, never a working checkout."""
    # If the repo ships its own CLAUDE.md at the pinned SHA, move it aside so BOTH arms generate from
    # the same blank-slate condition (recorded in the capture record for honesty).
    root_md = clone / "CLAUDE.md"
    shipped = root_md.exists()
    if shipped:
        root_md.rename(clone / "CLAUDE.md.repo-orig")

    cmd = [_CLAUDE, "-p", prompt,
           "--model", model,
           "--output-format", "json",
           "--permission-mode", "acceptEdits",   # let the arm WRITE CLAUDE.md non-interactively
           "--max-budget-usd", str(budget)]      # hard per-run spend ceiling
    if plugin_dir:                                # load a skill from a working tree (e.g. to test an un-installed fix)
        cmd += ["--plugin-dir", plugin_dir]
    proc = subprocess.run(cmd, cwd=str(clone), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")

    emitted = root_md.read_text(encoding="utf-8", errors="replace") if root_md.exists() else None

    # Parse the json single-result envelope defensively (field names can shift across CLI versions).
    cost_usd = usage = num_turns = None
    try:
        env = json.loads(proc.stdout)
        cost_usd = env.get("total_cost_usd", env.get("cost_usd"))
        usage = env.get("usage")
        num_turns = env.get("num_turns")
    except Exception:
        pass

    return {
        "returncode": proc.returncode,
        "repo_shipped_claude_md": shipped,
        "emitted_claude_md": emitted,
        "emitted_bytes": len(emitted.encode("utf-8")) if emitted is not None else 0,
        "emitted_lines": emitted.count("\n") + 1 if emitted else 0,
        "emitted_sha256": hashlib.sha256(emitted.encode("utf-8")).hexdigest() if emitted else None,
        "cost_usd": cost_usd,
        "usage": usage,
        "num_turns": num_turns,
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-500:],
    }


def probe(clone: Path, model: str, budget: float) -> int:
    """Stage-0: one cheap /init run on a throwaway clone. Report whether headless capture works."""
    if not (clone / ".git").exists():
        raise SystemExit(f"refuse: --probe needs a git clone at {clone}.")
    print(f"probe: claude {_claude_version()} · model={model} · running headless `/init` once …")
    r = run_arm(clone, INIT_PROMPT, model=model, budget=budget)
    _reset_pristine(clone)
    ok = r["returncode"] == 0 and r["emitted_claude_md"] is not None and r["emitted_bytes"] > 0
    print(f"  rc={r['returncode']}  emitted={'yes' if r['emitted_claude_md'] else 'NO'}"
          f"  bytes={r['emitted_bytes']}  cost_usd={r['cost_usd']}")
    if not ok and r["stderr_tail"].strip():
        print(f"  stderr tail: {r['stderr_tail'].strip()[-300:]}")
    print("VERDICT:", "PASS — headless /init capture works; the full matrix can proceed." if ok else
          "FAIL — headless /init did not emit a CLAUDE.md. Use the interactive-capture fallback (runbook).")
    return 0 if ok else 2


def capture_repo(repo: str, sha: str, clone: Path, *, key: str, runs_by_arm: dict, arms: list[str],
                 model: str, budget: float, date: str, plugin_dir: str | None = None) -> int:
    assert_pinned_clean(clone, sha)            # FAIL-CLOSED before we spend a token
    dest = OUT_ROOT / key
    record = {
        "schema": "deepinit-validation/m1b-init-capture/v1",
        "repo": repo, "key": key, "sha": sha, "model": model, "date": date,
        "claude_version": _claude_version(),
        "method": ("Both arms (/init · deepinit) on the SAME pinned clone — /init K runs (non-deterministic), "
                   "deepinit K runs; each arm writes a lean CLAUDE.md at the repo root, captured verbatim "
                   "here (the deepinit arm's .ai/ tree is snapshotted too). Cost is the run's real "
                   "total_cost_usd. CAPTURE-ONLY — blind scoring (grounding/faithfulness/dep-edge recall "
                   "vs validation/matrix/oracles/) is Stage 2."),
        "arms": {},
    }
    for arm in arms:
        prompt = INIT_PROMPT if arm == "init" else DEEPINIT_PROMPT
        k = runs_by_arm.get(arm, 1)
        arm_runs = []
        for n in range(1, k + 1):
            print(f"── {key} · {arm} · run {n}/{k} ──", flush=True)
            r = run_arm(clone, prompt, model=model, budget=budget,
                        plugin_dir=(plugin_dir if arm == "deepinit" else None))
            run_dir = dest / arm / f"run-{n}"
            run_dir.mkdir(parents=True, exist_ok=True)
            if r["emitted_claude_md"] is not None:
                (run_dir / "CLAUDE.md").write_text(r["emitted_claude_md"], encoding="utf-8")
            # The deepinit arm also emits the deep tier — snapshot .ai/ for the capability-delta + insights.
            if arm == "deepinit" and (clone / ".ai").exists():
                shutil.copytree(clone / ".ai", run_dir / ".ai", dirs_exist_ok=True)
            arm_runs.append({kk: vv for kk, vv in r.items()
                             if kk not in ("emitted_claude_md", "stdout_tail")})
            _reset_pristine(clone)
            if r["returncode"] != 0:
                print(f"   ! rc={r['returncode']} — see stderr tail:\n   {r['stderr_tail'].strip()[-300:]}", flush=True)
        record["arms"][arm] = {"prompt": prompt, "runs": arm_runs}

    dest.mkdir(parents=True, exist_ok=True)
    (dest / "_capture_record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"captured → {dest.relative_to(ROOT)}  (raw CLAUDE.md per arm/run + _capture_record.json)", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Metered DeepInit-vs-/init capture (Stage 1; env-guarded).")
    ap.add_argument("--probe", action="store_true", help="Stage-0: one cheap /init run; verify headless capture works")
    ap.add_argument("--repo", help="benchmark repo (owner/name), e.g. gin-gonic/gin")
    ap.add_argument("--sha", help="the pinned SHA the clone must be checked out at (fail-closed)")
    ap.add_argument("--clone", required=True, help="path to a THROWAWAY pinned clone (mutated + reset between runs)")
    ap.add_argument("--key", help="short evidence key (default: the repo's name after '/')")
    ap.add_argument("--init-runs", type=int, default=3, help="K /init runs (default 3 — /init is non-deterministic)")
    ap.add_argument("--deepinit-runs", type=int, default=1, help="K deepinit runs (default 1 — grounded/stable)")
    ap.add_argument("--arms", default="init,deepinit", help="comma list: init,deepinit (default both)")
    ap.add_argument("--model", default="opus", help="model alias/id, same for both arms (default opus)")
    ap.add_argument("--max-budget-usd", type=float, default=5.0, help="hard per-run spend ceiling")
    ap.add_argument("--plugin-dir", default=None, help="load the deepinit skill from this working tree (test an un-installed fix)")
    ap.add_argument("--date", default="", help="YYYY-MM-DD stamp for the capture record (no wall-clock in body)")
    args = ap.parse_args(argv)

    # THE on-switch — without it this is inert (CI can call it freely; it spends nothing).
    if os.environ.get(REAL_ENGINE_ENV) != "1":
        print(f"metered run skipped — set {REAL_ENGINE_ENV}=1 to capture (Stage 1, token-spending).")
        return 0

    clone = Path(args.clone)
    if args.probe:
        return probe(clone, args.model, args.max_budget_usd)

    if not (args.repo and args.sha):
        raise SystemExit("refuse: full capture needs --repo and --sha (the pinned head-to-head conditions).")
    if not args.date:
        raise SystemExit("refuse: pass --date YYYY-MM-DD (the capture record carries no wall clock).")
    key = args.key or args.repo.split("/")[-1]
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    runs_by_arm = {"init": args.init_runs, "deepinit": args.deepinit_runs}
    return capture_repo(args.repo, args.sha, clone, key=key, runs_by_arm=runs_by_arm, arms=arms,
                        model=args.model, budget=args.max_budget_usd, date=args.date, plugin_dir=args.plugin_dir)


if __name__ == "__main__":
    raise SystemExit(main())
