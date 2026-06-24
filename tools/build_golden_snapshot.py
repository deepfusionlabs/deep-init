#!/usr/bin/env python3
"""build_golden_snapshot.py — golden-output snapshot of a canonical end-to-end archive (M8-T4).

A NEW test modality: the §40 gate checks the archived e2e artifacts stay *valid*; this captures
their exact generated SHAPE so an UNINTENDED change is caught (drift) and an intended change forces
a deliberate snapshot refresh — distinguishing "the skill spec changed the output on purpose" from
"something silently drifted." (The same role golden/snapshot tests play in a normal test suite.)

The fingerprint is line-ending-normalised (LF) so it is byte-stable across a Windows/Unix checkout,
and it snapshots the docs-viewer MODEL (the template-independent parse of the archive) rather than the
rendered HTML, so a cosmetic template edit doesn't churn the golden while a real content/parser change
does. Harness §50 recomputes this and compares against the committed golden.

Usage:
  python tools/build_golden_snapshot.py <archive_dir>            # print the snapshot JSON
  python tools/build_golden_snapshot.py <archive_dir> --write    # (re)write _golden_snapshot.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# The stable text artifacts whose exact bytes we pin (normalised to LF).
HASHED_FILES = [
    "AGENTS.md",
    ".ai/docs/manifest.json",
    ".ai/deepinit.sarif",
    ".ai/docs/issues.md",
    ".ai/docs/decisions.md",
]


def _norm_hash(p: Path) -> str | None:
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def build_snapshot(archive: Path) -> dict:
    archive = Path(archive)
    # 1) byte hashes of the stable text artifacts
    file_hashes = {rel: _norm_hash(archive / rel) for rel in HASHED_FILES}

    # 2) structural fingerprint derived from the artifacts (human-readable "what changed")
    structural: dict = {}
    # component docs present
    comp_dir = archive / ".ai" / "docs" / "components"
    structural["component_docs"] = sorted(p.stem for p in comp_dir.glob("*.md")) if comp_dir.is_dir() else []
    # manifest component list
    man = archive / ".ai" / "docs" / "manifest.json"
    if man.exists():
        m = json.loads(man.read_text(encoding="utf-8"))
        comps = m.get("components")
        if isinstance(comps, dict):
            structural["manifest_components"] = sorted(comps.keys())
        elif isinstance(comps, list):
            structural["manifest_components"] = sorted(
                (c.get("name") if isinstance(c, dict) else str(c)) for c in comps)
    # SARIF rule ids + result count
    sarif = archive / ".ai" / "deepinit.sarif"
    if sarif.exists():
        s = json.loads(sarif.read_text(encoding="utf-8"))
        run = s["runs"][0]
        structural["sarif_version"] = s.get("version")
        structural["sarif_rule_ids"] = sorted(r["id"] for r in run["tool"]["driver"].get("rules", []))
        structural["sarif_result_count"] = len(run.get("results", []))

    # 3) docs-viewer MODEL hash (template-independent) — built from this archive
    viewer_model_hash = None
    viewer_struct: dict = {}
    try:
        import importlib.util
        bdv_path = Path(__file__).resolve().parent / "build_docs_viewer.py"
        spec = importlib.util.spec_from_file_location("build_docs_viewer_golden", bdv_path)
        bdv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bdv)
        model = bdv.build_model(archive)
        viewer_model_hash = hashlib.sha256(_canon(model).encode("utf-8")).hexdigest()
        viewer_struct = {
            "components": sorted(c.get("name", "") for c in model.get("components", [])),
            "decisions": len(model.get("decisions", []) or []),
            "issues": len(model.get("issues", []) or []),
            "search_index_len": len(model.get("search_index", []) or model.get("searchIndex", []) or []),
        }
    except Exception as e:  # noqa: BLE001 — recorded, not fatal (the viewer model is one of several signals)
        viewer_struct = {"error": str(e)}

    return {
        "schema": "deepinit-validation/golden-snapshot/v1",
        "archive": archive.name,
        "note": "Line-ending-normalised (LF) fingerprint of the canonical e2e archive. Regenerate "
                "DELIBERATELY (python tools/build_golden_snapshot.py <archive> --write) when a skill "
                "spec change intentionally alters the generated output; a drift is otherwise caught by §50.",
        "file_hashes": file_hashes,
        "structural": structural,
        "viewer_model_sha256": viewer_model_hash,
        "viewer_structural": viewer_struct,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Golden-output snapshot of a deep-init e2e archive")
    ap.add_argument("archive")
    ap.add_argument("--write", action="store_true", help="write _golden_snapshot.json into the archive dir")
    args = ap.parse_args(argv)
    archive = Path(args.archive).resolve()
    if not archive.is_dir():
        print(f"ERROR: not a directory: {archive}", file=sys.stderr)
        return 2
    snap = build_snapshot(archive)
    text = json.dumps(snap, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        out = archive / "_golden_snapshot.json"
        out.write_bytes(text.encode("utf-8"))   # LF, byte-stable
        print(f"wrote {out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
