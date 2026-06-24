#!/usr/bin/env python3
"""emit_projections.py — the multi-agent projections, really emitted (M8-Q6).

generation.md §"Multi-agent projections (D2-014)" specifies that DeepInit projects the LEAN tier
(AGENTS.md owned-region) to the other agent tools. §38 gated the SPEC; this is the deterministic
EMITTER that produces the real files for an archived run, and §57 gates their SHAPE.

Every projection is a deterministic transform of the ALREADY-redacted, already-verified lean tier:
it adds NO new findings, never carries a deep `ISS-` defect (R9 — issues never enter an always-loaded
surface), opens with a "canonical context lives in <source>" note (the source is AGENTS.md, or CLAUDE.md
on a Claude-Code-native archive with no AGENTS.md — ISS-005) so the projections never diverge from the
source of truth, and (for the file-writing ones) honors the owned-region + .bak discipline.

Targets:
  - CLAUDE.md                          (Claude Code — owned-region block + @.ai/docs import pointers)
  - .github/copilot-instructions.md    (GitHub Copilot — plain-markdown repo-wide instructions)
  - .windsurf/rules/deepinit-lean.md   (Windsurf — an always-on lean-highlights rule)
  - .cursorrules                       (Cursor — lean highlights as a rules file)

Usage:
  python tools/emit_projections.py <archive_dir>            # print a summary of what WOULD emit
  python tools/emit_projections.py <archive_dir> --write    # write the projection files into the archive
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

START = "<!-- DEEPINIT:START"
END = "<!-- DEEPINIT:END -->"

# The lean-tier SOURCE is the canonical context file: AGENTS.md when it carries a DeepInit owned region (the
# cross-tool export path), else CLAUDE.md (a Claude-Code-NATIVE archive under the front-door model). Parameterized
# so a Claude-native run with NO root AGENTS.md projects from CLAUDE.md instead of raising (ISS-005). The CANON note
# + provenance name the actual source, so a projection never points at a file the archive doesn't have.
_CANONICAL_PREFERENCE = ("AGENTS.md", "CLAUDE.md")


def _canon_note(canonical: str) -> str:
    return (f"> Canonical context lives in **{canonical}** + **.ai/docs/** — this file is a generated projection "
            f"of the lean tier; do not edit inside the DeepInit markers (regenerated each run).")


def _detect_canonical(archive: Path) -> str:
    """The lean-tier source basename: the first of AGENTS.md / CLAUDE.md that exists with a COMPLETE DeepInit
    owned region (BOTH the START and END markers — a truncated region would crash `_owned_body` downstream,
    so it's never selected here; the caller gets the clean 'no canonical lean tier' error instead)."""
    for name in _CANONICAL_PREFERENCE:
        p = archive / name
        if p.exists():
            text = p.read_text(encoding="utf-8")
            if START in text and END in text:
                return name
    raise ValueError("no canonical lean tier (AGENTS.md or CLAUDE.md) with a DeepInit owned region in the archive")


def _owned_body(canonical_md: str) -> tuple[str, str]:
    """Return (provenance_comment, lean_body) from the canonical lean tier's owned region."""
    s = canonical_md.find(START)
    e = canonical_md.find(END)
    if s < 0 or e < 0:
        raise ValueError("the canonical lean tier has no DeepInit owned region")
    inner = canonical_md[canonical_md.find("-->", s) + 3:e].strip("\n")
    # strip a leading provenance comment block if present
    prov = ""
    m = re.match(r"\s*<!--(.*?)-->\s*", inner, re.DOTALL)
    if m:
        prov = m.group(1).strip()
        inner = inner[m.end():]
    return prov, inner.strip("\n")


def _provenance_block(run_id: str, target: str, canonical: str = "AGENTS.md") -> str:
    return (f"<!--\n  DeepInit projection provenance (R3)\n  stage:   EMIT → PROJECT ({target})\n"
            f"  run_id:  {run_id}\n  source:  {canonical} (lean tier) — deterministic projection, no new findings\n"
            f"  note:    content inside the DEEPINIT markers is owned + regenerated; edit OUTSIDE them.\n-->")


def _run_id(prov: str) -> str:
    # Provenance comes in two shapes (B5): the multi-line block (`run_id:  <id>`) AND the single-line
    # pipe-delimited Emit header (`DeepInit Emit | system-wide | Run <id> @<sha> | Generated <date>`).
    # Parse BOTH so a projection never falls back to the cosmetic "run-unknown".
    m = re.search(r"run_id:\s*(\S+)", prov) or re.search(r"\bRun\s+(\S+)", prov)
    return m.group(1) if m else "run-unknown"


def _wrap(body: str, run_id: str, target: str, title: str, canonical: str = "AGENTS.md") -> str:
    return (f"{START} (managed — regenerated each run; edit OUTSIDE these markers) -->\n"
            f"{_provenance_block(run_id, target, canonical)}\n# {title}\n\n{_canon_note(canonical)}\n\n{body}\n{END}\n")


def build_projections(archive: Path, canonical: str | None = None) -> dict[str, str]:
    canonical = canonical or _detect_canonical(archive)
    src = (archive / canonical).read_text(encoding="utf-8")
    prov, body = _owned_body(src)
    run_id = _run_id(prov)
    # R9 safety: a lean tier must carry NO deep defect id; strip any stray ISS- line defensively.
    body = "\n".join(ln for ln in body.splitlines() if "ISS-" not in ln)
    out = {
        "CLAUDE.md": _wrap(body, run_id, "CLAUDE.md", "Agent Context (Claude Code projection)", canonical),
        ".github/copilot-instructions.md": _wrap(body, run_id, "copilot", "Repository instructions (Copilot projection)", canonical),
        ".windsurf/rules/deepinit-lean.md": _wrap(body, run_id, "windsurf", "DeepInit lean rules (Windsurf, always-on)", canonical),
        ".cursorrules": _wrap(body, run_id, "cursor", "DeepInit lean rules (Cursor)", canonical),
    }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Emit the multi-agent projections from an archived lean tier")
    ap.add_argument("archive")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    archive = Path(args.archive).resolve()
    try:
        canonical = _detect_canonical(archive)
    except ValueError as e:
        print(f"ERROR: {e} (looked in {archive})", file=sys.stderr)
        return 2
    print(f"# canonical lean source: {canonical}")
    projections = build_projections(archive, canonical)
    for rel, content in projections.items():
        if args.write:
            dest = archive / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.with_suffix(dest.suffix + ".bak").write_bytes(dest.read_bytes())  # .bak before overwrite
            dest.write_text(content, encoding="utf-8")
            print(f"wrote {rel} ({len(content)} bytes)")
        else:
            print(f"would emit {rel} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
