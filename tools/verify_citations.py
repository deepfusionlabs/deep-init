#!/usr/bin/env python3
"""verify_citations.py — portable, cross-platform citation verifier (M8-A4).

DeepInit's verification stage (global-rules R1, verification.md) checks that EVERY `file:line` citation
in the generated docs actually resolves against the source. The M5 dogfood surfaced that the ad-hoc bash
one-liner verifier SIGPIPE-crashed under MSYS/Git-Bash — a portability defect. This is the small, pure-Python
replacement the skill can shell to on ANY platform (Windows/macOS/Linux), with no pipes, no shell quoting,
no SIGPIPE surface.

It scans the docs for `path:line` and `path:line-line` citations, resolves each against a repo root, and
reports resolved vs broken with the exact reason (missing file / line out of range). Exit 0 iff every
citation resolves (so it doubles as a gate for the skill's Verify stage and for CI).

Usage:
  python tools/verify_citations.py <docs_dir_or_file> --repo <repo_root>
  python tools/verify_citations.py AGENTS.md --repo . --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# A citation: a path (with a slash and an extension-ish tail) followed by :line or :line-line.
# Conservative — requires a path separator OR a dotted filename so prose like "ratio 3:1" isn't matched.
_CITE = re.compile(r"(?<![\w.])((?:[\w./\-]+/)?[\w\-]+\.[\w]+):(\d+)(?:-(\d+))?")

# Files whose lines shift WHOLESALE on a routine change (regenerated docs, append-mostly logs): a `:line` cite into
# one of these resolves but silently points at the WRONG content after a bump (LESSON 1b). Cite them at file level.
SHIFTING_FILES = {"CHANGELOG.md", "STATS.json"}

# Directories never worth indexing for bare-basename normalization (VCS / deps / build output).
_INDEX_SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".mypy_cache", ".pytest_cache"}


def _index_basenames(repo: Path) -> dict:
    """basename → sorted list of repo-relative POSIX paths, for normalizing a bare citation to its unique file.
    Bounded: skips VCS / dependency / build-output dirs so it stays cheap on a real repo."""
    idx: dict = {}
    for p in repo.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo)
        if _INDEX_SKIP & set(rel.parts):
            continue
        idx.setdefault(p.name, []).append(rel.as_posix())
    return {k: sorted(v) for k, v in idx.items()}


def _line_count(p: Path) -> int:
    try:
        with p.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except Exception:  # noqa: BLE001
        return -1


def find_citations(text: str) -> list[tuple[str, int, int]]:
    """Return [(path, start_line, end_line)] for every citation in `text`."""
    out = []
    for m in _CITE.finditer(text):
        path, a, b = m.group(1), int(m.group(2)), m.group(3)
        out.append((path, a, int(b) if b else a))
    return out


def verify(docs: Path, repo: Path, normalize: bool = True) -> dict:
    docs = Path(docs)
    repo = Path(repo)
    files = [docs] if docs.is_file() else sorted(p for p in docs.rglob("*.md"))
    resolved, broken, normalized, shifting = [], [], [], []
    index = None  # basename → [repo-relative paths]; built lazily on the first bare miss
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for path, a, b in find_citations(text):
            cite_path = path
            # LESSON 1 — normalize a BARE basename (no path separator) that does not resolve as-is to its UNIQUE
            # repo-relative path; an AMBIGUOUS one is flagged, never silently resolved to the wrong same-named file.
            if normalize and ("/" not in path and "\\" not in path) and not (repo / path).is_file():
                if index is None:
                    index = _index_basenames(repo)
                cands = index.get(path, [])
                if len(cands) == 1:
                    cite_path = cands[0]
                    normalized.append({"from": path, "to": cite_path})
                elif len(cands) > 1:
                    broken.append({"doc": f.name, "cite": f"{path}:{a}" + (f"-{b}" if b != a else ""),
                                   "reason": f"ambiguous bare citation path — matches {len(cands)} files "
                                             f"({', '.join(cands[:4])}{'…' if len(cands) > 4 else ''}); "
                                             f"use a full repo-relative path"})
                    continue
            target = (repo / cite_path)
            rec = {"doc": f.name, "cite": f"{cite_path}:{a}" + (f"-{b}" if b != a else "")}
            if not target.is_file():
                broken.append({**rec, "reason": "file not found"})
                continue
            n = _line_count(target)
            if n < 0:
                broken.append({**rec, "reason": "unreadable file"})
            elif a < 1 or b > n:
                broken.append({**rec, "reason": f"line out of range (file has {n} lines)"})
            else:
                resolved.append(rec)
                # LESSON 1b — a line-cite into an inherently-shifting / regenerated file resolves but silently rots
                # on a bump; surface it as a warning (never a failure — the citation does resolve).
                if cite_path.replace("\\", "/").split("/")[-1] in SHIFTING_FILES:
                    shifting.append(rec["cite"])
    return {
        "schema": "deepinit/citation-verification/v1",
        "docs": str(docs), "repo": str(repo),
        "checked": len(resolved) + len(broken),
        "resolved": len(resolved),
        "broken": broken,
        "normalized": normalized,
        "shifting_line_cites": shifting,
        "all_resolved": not broken,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portable cross-platform file:line citation verifier")
    ap.add_argument("docs", help="a docs file or directory")
    ap.add_argument("--repo", default=".", help="repo root the citations resolve against")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = verify(Path(args.docs), Path(args.repo))
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"citations: {res['resolved']}/{res['checked']} resolved"
              + (f" · {len(res['broken'])} BROKEN" if res["broken"] else " · all resolved")
              + (f" · {len(res['normalized'])} normalized" if res.get("normalized") else ""))
        for b in res["broken"][:50]:
            print(f"  [BROKEN] {b['doc']}: {b['cite']} — {b['reason']}")
        for s in res.get("shifting_line_cites", [])[:20]:
            print(f"  [WARN shifting] {s} — line-cite into a regenerated/shifting file; cite at file level (LESSON 1b)")
    return 0 if res["all_resolved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
