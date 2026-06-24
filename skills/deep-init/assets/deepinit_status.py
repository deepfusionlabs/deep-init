#!/usr/bin/env python3
"""deepinit_status.py — DeepInit deterministic staleness check (NO LLM, NO network).

The hook- and session-start-callable core of `--lint`: it compares the committed
`.ai/docs/current/.file_hashes.json` against the working tree and reports how far the
generated docs have drifted from the code. Pure stdlib — safe to call from a git
post-commit hook or a Claude Code SessionStart hook (neither can summon a Claude session,
so the staleness signal must be deterministic).

It embodies the update.md Step-0 contract: the content-hash comparison is the
**authoritative, git-independent** detector; a stored file absent from disk is a
**removed** (caught by iterating the STORED set, not just the current tree — the symmetric
set-diff, harness §64); `.pending_changes.txt` (written by post-commit.sh) is an
**advisory** accelerator, never the source of truth.

Exit code: 0 = fresh (or no DeepInit state yet — never an error on a fresh checkout),
1 = stale. Shipped in the skill's assets/ so `setup-hooks` can install it into a consumer
repo; `tools/` stays dev-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# DeepInit's generated state lives at .ai/docs/ (the current product layout) OR .ai/docs/current/
# (the versioned layout the spec + the mini-update fixture use). Resolve whichever carries the manifest.
STATE_DIRS = (Path(".ai/docs"), Path(".ai/docs/current"))
HASHES = ".file_hashes.json"
PENDING = ".pending_changes.txt"


def resolve_state(root: Path):
    """Return the dir holding `.file_hashes.json` (flat `.ai/docs` or versioned `.ai/docs/current`), or None."""
    for d in STATE_DIRS:
        if (root / d / HASHES).exists():
            return root / d
    return None


def _sha256(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def stored_files(data: dict) -> dict:
    """{rel_path: stored_sha_or_None} from either `.file_hashes.json` schema shape.

    - per-file schema   {"files": {rel: {"sha256": ...}}}              → per-file sha (content-checkable)
    - per-component schema {"components": {c: {"files": [rel, ...]}}}  → existence-only (sha None;
      the per-component content_hash is not a per-file hash, so the lean status check can only
      detect a *removed* file there — the full per-component compare is `--update`/`--lint`).
    """
    out: dict = {}
    if not isinstance(data, dict):
        return out
    # Shape 1 — wrapped per-file: {"files": {rel: {"sha256": ...}}} (or rel: "<sha>")
    files = data.get("files")
    if isinstance(files, dict):
        for rel, rec in files.items():
            if isinstance(rec, dict):
                out[rel] = rec.get("sha256") or rec.get("content_hash")
            elif isinstance(rec, str):
                out[rel] = rec
    # Shape 2 — per-component: {"components": {c: {"files": [rel, ...]}}} (existence-only; sha None)
    comps = data.get("components")
    if isinstance(comps, dict):
        for rec in comps.values():
            for rel in (rec or {}).get("files", []) or []:
                out.setdefault(rel, None)
    # Shape 3 — flat {rel_path: "<sha-hex>"} (the current emitted layout). A top-level entry counts
    # as a tracked file iff its value is a hex digest and its key isn't a wrapper/meta field.
    _META = {"version", "schema", "schema_version", "generated", "run_id", "files", "components"}
    for k, v in data.items():
        if k in _META:
            continue
        if isinstance(v, str) and len(v) >= 32 and all(c in "0123456789abcdefABCDEF" for c in v):
            out.setdefault(k, v.lower())
    return out


def stored_components(data: dict) -> dict:
    """{rel_path: component_name} when the baseline carries per-file component ownership; else {}.

    Best-effort, never raises: the wrapped per-file schema (`{"files": {rel: {"component": …}}}`) and the
    per-component schema (`{"components": {c: {"files": […]}}}`) both name the owning component, so the nudge
    can say *which components* drifted. The current flat `{rel: "<sha>"}` product layout has no component
    field — this returns {} there and the change summary falls back to bare paths (still useful).
    """
    out: dict = {}
    if not isinstance(data, dict):
        return out
    files = data.get("files")
    if isinstance(files, dict):
        for rel, rec in files.items():
            if isinstance(rec, dict) and isinstance(rec.get("component"), str):
                out[rel] = rec["component"]
    comps = data.get("components")
    if isinstance(comps, dict):
        for cname, rec in comps.items():
            for rel in (rec or {}).get("files", []) or []:
                out.setdefault(rel, cname)
    return out


def diff_stored(stored: dict, root: Path) -> tuple:
    """Symmetric set-diff of the STORED file set against the working tree.

    Iterating the stored keys (not just the current tree) is what catches a removed file —
    the deletion case a one-directional 'for each current file' loop silently misses.
    """
    modified, removed = [], []
    for rel, sha in sorted(stored.items()):
        cur = _sha256(root / rel)
        if cur is None:
            removed.append(rel)
        elif sha is not None and cur != sha:
            modified.append(rel)
    return modified, removed


def read_pending(state: Path) -> list:
    pp = state / PENDING
    if not pp.exists():
        return []
    seen, out = set(), []
    for line in pp.read_text(encoding="utf-8", errors="replace").splitlines():
        f = line.strip()
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def compute_status(root: Path) -> dict:
    state = resolve_state(root)
    if state is None:
        return {"available": False, "stale": False,
                "reason": "no .file_hashes.json (run deep-init first)",
                "tracked": 0, "modified": [], "removed": [], "pending": []}
    hp = state / HASHES
    try:
        data = json.loads(hp.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"available": False, "stale": False,
                "reason": f"unreadable .file_hashes.json: {e}",
                "tracked": 0, "modified": [], "removed": [], "pending": []}
    stored = stored_files(data)
    modified, removed = diff_stored(stored, root)
    pending = read_pending(state)
    return {"available": True, "stale": bool(modified or removed or pending),
            "tracked": len(stored), "modified": modified, "removed": removed, "pending": pending}


def human(s: dict) -> str:
    if not s["available"]:
        return f"deep-init: {s['reason']}"
    if not s["stale"]:
        return f"deep-init: docs fresh ({s['tracked']} files tracked)."
    parts = []
    if s["modified"]:
        parts.append(f"{len(s['modified'])} modified")
    if s["removed"]:
        parts.append(f"{len(s['removed'])} removed")
    if s["pending"]:
        parts.append(f"{len(s['pending'])} pending")
    return ("deep-init: docs STALE (" + ", ".join(parts) + ") - run /deep-init:refresh to "
            "refresh (or /deep-init:check for detail).")


def change_summary(status: dict, components: dict | None = None, limit: int = 6) -> str:
    """A compact, deterministic, clock-free list of WHAT changed — for the proactive nudge.

    Lists the first `limit` changed paths (modified + removed + pending, de-duplicated, sorted) with a
    `(+K more)` tail, and — when a {path: component} map is available (see `stored_components`) — which
    components those files belong to in a trailing `[comp, …]`. Returns "" when nothing changed or the
    baseline is unavailable. Byte-stable (sorted, no clock) so the SessionStart e2e can pin it; this is the
    detail the count-only `human()` line never showed, so the user sees *what* drifted, not just *how many*.
    """
    if not status.get("available") or not status.get("stale"):
        return ""
    seen, paths = set(), []
    for rel in [*status.get("modified", []), *status.get("removed", []), *status.get("pending", [])]:
        if rel and rel not in seen:
            seen.add(rel)
            paths.append(rel)
    paths.sort()
    shown = paths[:limit]
    tail = f" (+{len(paths) - len(shown)} more)" if len(paths) > len(shown) else ""
    listing = ", ".join(shown) + tail
    if components:
        comps = sorted({components[p] for p in paths if components.get(p)})
        if comps:
            listing += "  [" + ", ".join(comps[:6]) + ("…" if len(comps) > 6 else "") + "]"
    return listing


def summary_for(root: Path, status: dict | None = None) -> str:
    """The change-summary string for a repo (loads the baseline's component map best-effort).

    Pass a precomputed `status` to avoid re-hashing the tree when the caller already has it
    (the `--summary` CLI path does — one compute_status per invocation, not two).
    """
    s = status if status is not None else compute_status(root)
    components: dict = {}
    state = resolve_state(root)
    if state is not None:
        try:
            components = stored_components(json.loads((state / HASHES).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            components = {}
    return change_summary(s, components)


# ── freshness-nudge diagnostics (--explain): why the SessionStart nudge would / wouldn't fire now ──
# Clock-free + deterministic so it is harness-testable: it reports the FACTS the bash hook gates on
# (staleness, the disable switches, the cadence/window, the last-nudge state) and the resulting verdict,
# mirroring session-start.sh's decision logic — without consulting the wall clock.
_CFG = ".ai/deepinit.config"
_NO_NUDGE = ".claude/.deepinit-no-nudge"
_NUDGE_STATE = ".ai/.deepinit-nudge-state"
_CADENCES = ("session", "window", "always")


def _cfg_text(root: Path) -> str:
    p = root / _CFG
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except OSError:
        return ""


def _cfg_str(text: str, key: str, default: str) -> str:
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', text)
    return m.group(1) if m else default


def _cfg_num(text: str, key: str, default):
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*([0-9][0-9.]*)', text)
    if not m:
        return default
    v = float(m.group(1))
    return int(v) if v == int(v) else v


def explain(root: Path) -> dict:
    """Deterministic 'would the SessionStart nudge fire now?' diagnostic — same gates as session-start.sh."""
    st = compute_status(root)
    cfg = _cfg_text(root)
    disabled = []
    if (root / _NO_NUDGE).exists():
        disabled.append(".claude/.deepinit-no-nudge")
    if _cfg_str(cfg, "notify-on-session-start", "on") == "off" or _cfg_str(cfg, "check-on-session-start", "on") == "off":
        disabled.append('notify-on-session-start:"off"')
    cadence = _cfg_str(cfg, "notify-cadence", "session")
    if cadence not in _CADENCES:
        cadence = "session"
    window_hours = _cfg_num(cfg, "notify-window-hours", 6)
    state_p = root / _NUDGE_STATE
    last = None
    if state_p.exists():
        try:
            last = state_p.read_text(encoding="utf-8").strip() or None
        except OSError:
            last = None
    if not st["available"]:
        verdict, why = "no", f"no DeepInit state ({st['reason']})"
    elif not st["stale"]:
        verdict, why = "no", "docs are fresh — nothing to nudge"
    elif disabled:
        verdict, why = "no", "disabled by " + ", ".join(disabled)
    elif cadence == "always":
        verdict, why = "yes", "stale + cadence=always — fires every session start"
    elif cadence == "window":
        verdict, why = "per-window", f"stale — fires at most once per {window_hours}h (last: {last or 'never'})"
    else:
        verdict, why = "new-session-only", f"stale — fires once per new session (last session: {last or 'never'})"
    return {"available": st["available"], "stale": st["stale"], "tracked": st["tracked"],
            "modified": st["modified"], "removed": st["removed"], "pending": st["pending"],
            "nudge_disabled_by": disabled, "cadence": cadence, "window_hours": window_hours,
            "last_nudge_state": last, "would_nudge": verdict, "why": why}


def human_explain(e: dict) -> str:
    docs = (f"STALE ({len(e['modified'])} modified, {len(e['removed'])} removed, {len(e['pending'])} pending)"
            if e["stale"] else ("fresh" if e["available"] else "no DeepInit state"))
    enabled = ("no - " + ", ".join(e["nudge_disabled_by"])) if e["nudge_disabled_by"] else "yes"
    verdict = {"yes": "WOULD NUDGE", "no": "SILENT",
               "new-session-only": "WOULD NUDGE (once per new session)",
               "per-window": f"WOULD NUDGE (once per {e['window_hours']}h window)"}[e["would_nudge"]]
    cad = e["cadence"] + (f" (window {e['window_hours']}h)" if e["cadence"] == "window" else "")
    return ("DeepInit freshness - would the SessionStart nudge fire now?\n"
            f"  docs:             {docs}\n"
            f"  nudge enabled:    {enabled}\n"
            f"  cadence:          {cad}\n"
            f"  last-nudge state: {e['last_nudge_state'] or 'none'}  (.ai/.deepinit-nudge-state)\n"
            f"  verdict:          {verdict} - {e['why']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="DeepInit deterministic staleness check (no LLM, no network).")
    ap.add_argument("--root", default=".", help="repo root to check (default: cwd)")
    ap.add_argument("--json", action="store_true", help="emit the status as JSON")
    ap.add_argument("--quiet", action="store_true", help="print nothing when fresh / no state")
    ap.add_argument("--explain", action="store_true",
                    help="diagnose WHY the SessionStart nudge would / wouldn't fire now (stale? disabled? cadence?)")
    ap.add_argument("--summary", action="store_true",
                    help="print the status line, then (if stale) a second line listing WHAT changed (paths + components)")
    a = ap.parse_args(argv)
    if a.explain:
        e = explain(Path(a.root))
        print(json.dumps(e, indent=2, sort_keys=True) if a.json else human_explain(e))
        return 0
    if a.summary:
        s = compute_status(Path(a.root))
        cs = summary_for(Path(a.root), s)   # reuse the status we just computed (no second tree-hash)
        if a.json:
            print(json.dumps({**s, "summary": cs}, indent=2, sort_keys=True))
        else:
            print(human(s))          # line 1 — the canonical STALE/fresh line (the cross-file grep contract)
            if cs:
                print(cs)            # line 2 — what changed (emitted only when stale)
        return (1 if s["stale"] else 0)   # parenthesised so the §65 status-exit mutation still targets the default path below
    s = compute_status(Path(a.root))
    if a.json:
        print(json.dumps(s, indent=2, sort_keys=True))
    elif not (a.quiet and not s["stale"]):
        print(human(s))
    return 1 if s["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())
