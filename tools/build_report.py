#!/usr/bin/env python3
"""
build_report.py — DeepInit unified Report (Docs + Insights, one file)

Builds ONE self-contained, OFFLINE report.html that merges the docs reader
(the "Docs" view) and the metrics / issue dashboard (the "Insights" view) into
a single co-branded artifact (DeepInit, by DeepFusion Labs). It REUSES
build_docs_viewer's tolerant parsers (the spec<->impl mirror — one source of
truth for parsing AGENTS.md/CLAUDE.md + .ai/docs/**), then adds an Insights
data block and injects the model into report-template.html.

Same hard constraints as the viewer/dashboard (AF-6 license-clean; harness §43):
one self-contained file, vanilla JS + inline CSS, NO framework / NO CDN /
NO external src|href / no fetch|XHR (opens from file://).

Honest-degrade (R1): the Insights risk heatmap is populated from the manifest's
components.<name>.metrics block when present; when absent it is shown as
"unavailable" (with a real documented-files footprint fallback), never as a
misleading zero.

Usage:
  python tools/build_report.py <output_dir> [-o <out.html>]
    <output_dir>  a dir containing CLAUDE.md/AGENTS.md and .ai/docs/
    -o            output path (default: <output_dir>/.ai/report.html)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import build_docs_viewer as bdv  # reuse the tolerant parsers + escaped-embed render

SEV_KEYS = {"critical", "high", "medium", "low", "cosmetic"}
SEV_ALIASES = {
    "crit": "critical", "hi": "high", "med": "medium", "lo": "low",
    "info": "cosmetic", "trivial": "cosmetic", "nit": "cosmetic",
}


def _norm_sev(s: str) -> str:
    s = (s or "").strip().lower()
    return s if s in SEV_KEYS else SEV_ALIASES.get(s, s)


def build_timing_panel(manifest: dict) -> dict:
    """The Insights "where the time went" block — derived from the manifest's schema-5
    `processing_metrics` (per-stage `duration_sec` + throughput/parallelism).

    Honest-degrade (R1): a schema-4 manifest with NO `processing_metrics` (the dominant case
    until a run records timing) yields available=False ("timing unavailable") — never a
    fabricated zero. `time_source` rides along so the view can flag a self-stamped split as an
    estimate (a Claude instance has no trustworthy clock — generation.md timing ladder); only an
    `external_metered` total is a measured wall-clock figure, never published from here.
    """
    pm = manifest.get("processing_metrics") or {}
    rows = []
    for s in (pm.get("stages") or []):
        if not isinstance(s, dict):
            continue
        dur = s.get("duration_sec")
        rows.append({"name": s.get("name", ""), "duration_sec": (float(dur) if dur is not None else None)})
    if not rows:
        return {"available": False, "stages": [], "total_sec": None, "time_source": None}
    durs = [r["duration_sec"] for r in rows if r["duration_sec"] is not None]
    return {
        "available": True,
        "stages": rows,
        "total_sec": round(sum(durs), 1) if durs else None,
        "time_source": pm.get("time_source"),
        "throughput": pm.get("throughput") or {},
        "parallelism": pm.get("parallelism") or {},
    }


def build_dashboard(model: dict, manifest: dict) -> dict:
    """The Insights data island — derived from the manifest + parsed ledger.

    severity is taken from the manifest's authoritative by_severity when
    present (so the donut never disagrees with the run manifest), else derived
    from the parsed verified issues.
    """
    issues = model.get("issues", {}) or {}
    verified = issues.get("verified", []) or []

    sev: dict[str, int] = {}
    mi_by = ((manifest.get("issues") or {}).get("by_severity")) or {}
    if mi_by:
        for k, v in mi_by.items():
            nk = _norm_sev(k)
            sev[nk] = sev.get(nk, 0) + int(v or 0)
    else:
        for v in verified:
            nk = _norm_sev(v.get("severity"))
            if nk:
                sev[nk] = sev.get(nk, 0) + 1

    mi = manifest.get("issues") or {}
    open_n = mi.get("open")
    if open_n is None:
        open_n = len(verified)
    resolved = mi.get("resolved") or 0

    # risk metrics — only available if the skill persisted them to the manifest
    comps_meta = manifest.get("components") or {}
    risk_components: list[dict] = []
    available = False
    for name, meta in comps_meta.items():
        m = ((meta or {}).get("metrics")) or {}
        if m:
            available = True
            risk_components.append({
                "name": name,
                "risk": float(m.get("risk", 0) or 0),
                "churn": m.get("churn"),
                "bus_factor": m.get("bus_factor"),
                "coverage": m.get("coverage"),
                "criticality": m.get("criticality", ""),
            })

    drift_rows = manifest.get("drift") or []
    db_verified = bool(manifest.get("db_verified"))

    return {
        "severity": sev,
        "open": open_n,
        "resolved": resolved,
        "risk": {"available": available, "components": risk_components},
        "drift": {"available": bool(db_verified and drift_rows), "rows": drift_rows},
        "db_verified": db_verified,
        "timing": build_timing_panel(manifest),
    }


def graph_from_structural(sg: dict, manifest: dict | None = None) -> dict:
    """Component dependency graph for the Insights + interactive Map views.

    Reads the structural-graph.json the Detect stage already emits (via
    tools/graphify_adapter.py); changes NO scanning/analysis. Returns a small,
    byte-stable {available, nodes, edges} block. Each NODE carries the data the
    navigable Map view needs: `id` (component), `anchor` ("c-<slug>" — the Docs
    route a node click navigates to), `files`/`exports` counts (node sizing),
    `in_deg`/`out_deg` (degree, from imported_by/imports_from), `risk`+`criticality`
    (from the manifest metrics, for the risk tint — None when unscored, never a
    misleading 0, R1), and a deterministic preset position `x`/`y` (a stable ring
    laid out in Python so the build stays byte-stable and the view reproducible;
    Cytoscape adds pan/zoom/drag on top). EDGES are component->component
    `imports_from` relationships (weight = #symbols, dir = "out").
    Honest-degrade (R1): an absent / shapeless graph yields available=False (the
    views then show an honest "unavailable" state, never a fabricated diagram).
    Symbol-level / whole-codebase drill-down stays DeepMap's lane."""
    comps = (sg or {}).get("components")
    if not isinstance(comps, dict) or not comps:
        return {"available": False, "nodes": [], "edges": []}
    # risk/criticality from the manifest (same source build_dashboard reads), per component
    risk_by_name: dict[str, tuple] = {}
    for nm, meta in ((manifest or {}).get("components") or {}).items():
        m = ((meta or {}).get("metrics")) or {}
        if m:
            r = m.get("risk")
            risk_by_name[nm] = (float(r) if r is not None else None, str(m.get("criticality", "") or ""))
    names = sorted(comps.keys())
    N = len(names)
    radius = max(160, N * 26)  # deterministic ring radius (no RNG/clock)
    nodes = []
    for i, n in enumerate(names):
        c = comps.get(n) or {}
        ang = (-math.pi / 2 + (i / N) * 2 * math.pi) if N else 0.0
        risk, crit = risk_by_name.get(n, (None, ""))
        nodes.append({
            "id": n,
            "anchor": "c-" + bdv._slug(n),
            "files": len((c.get("files")) or []),
            "exports": len((c.get("exports")) or []),
            "in_deg": len((c.get("imported_by")) or {}),
            "out_deg": len((c.get("imports_from")) or {}),
            "risk": risk,
            "criticality": crit,
            "x": round(radius * math.cos(ang), 2),
            "y": round(radius * math.sin(ang), 2),
        })
    edges, seen = [], set()
    for n in names:
        imports_from = ((comps.get(n) or {}).get("imports_from")) or {}
        for tgt in sorted(imports_from.keys()):
            if tgt in comps and tgt != n and (n, tgt) not in seen:
                seen.add((n, tgt))
                edges.append({"from": n, "to": tgt, "weight": len(imports_from.get(tgt) or []), "dir": "out"})
    return {"available": True, "nodes": nodes, "edges": edges}


def _graph_provenance(sg: dict, path: Path) -> dict:
    """Honest provenance for the Map view (Tier-2/3 freshness fix).

    Reports WHEN the structural graph was built (the file's mtime → an `as_of` DATE,
    distinct from the report's own build time) and WHICH edge classes the analysis
    actually had (imports always; calls / inheritance only on the v2 Graphify path).
    This is what stops the report from *looking* freshly-built while embedding a months-
    old map: the Map now carries its own honest date and scope. DATE only (no clock) so
    it stays deterministic given the file. `refreshed_on_update=True` records that
    `--update` now rebuilds the graph (it was frozen between full runs before)."""
    import datetime as _dt
    comps = (sg or {}).get("components", {}) or {}
    classes = ["imports"]
    if any((c.get("calls_into") or c.get("called_by")) for c in comps.values()):
        classes.append("calls")
    if any((c.get("inherits_from") or c.get("inherited_by")) for c in comps.values()):
        classes.append("inheritance")
    try:
        as_of = _dt.datetime.fromtimestamp(path.stat().st_mtime, _dt.timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        as_of = None
    return {"as_of": as_of, "schema_version": (sg or {}).get("version"),
            "edge_classes": classes, "refreshed_on_update": True}


def build_graph(out_dir: Path, manifest: dict | None = None) -> dict:
    """Find + read the existing structural-graph.json (build_report emits no graph) and
    shape it for the Insights diagram + the navigable Map view. Tries the Detect output
    path first, then fallbacks. `manifest` supplies per-component risk tints. When the
    graph is present, attach honest `provenance` (as-of date + edge classes) so the Map
    is dated/scoped rather than silently passing off a stale graph as current."""
    out_dir = Path(out_dir)
    for cand in (out_dir / ".ai" / "docs" / "current" / "structural-graph.json",
                 out_dir / ".ai" / "docs" / "structural-graph.json",
                 out_dir / "structural-graph.json"):
        if cand.exists():
            try:
                sg = json.loads(cand.read_text(encoding="utf-8"))
                block = graph_from_structural(sg, manifest)
                if block.get("available"):
                    block["provenance"] = _graph_provenance(sg, cand)
                return block
            except Exception:
                pass
    return {"available": False, "nodes": [], "edges": []}


def build_report_model(out_dir: Path) -> dict:
    # ISS-010: the dogfood "## ISS-NNN —" / "### ADR-N —" ledger shapes are now parsed by the ONE
    # shared build_docs_viewer parser (one source of truth — report.md), which also derives the
    # anchor/xref/search_index entries. No divergent dup parser here anymore.
    model = bdv.build_model(out_dir)
    model["counts"]["verified_issues"] = len(model["issues"].get("verified", []))
    model["counts"]["adrs"] = len(model.get("decisions", []))
    model["dashboard"] = build_dashboard(model, model.get("manifest") or {})
    model["dashboard"]["graph"] = build_graph(out_dir, model.get("manifest") or {})  # reads the existing structural-graph.json (+ manifest risk tints)
    model["schema"] = "deepinit-report/v1"
    return model


VENDOR_DIR = Path(__file__).resolve().parent.parent / "skills" / "deep-init" / "assets" / "vendor"
VENDOR_SUBS = {
    "/*__VENDOR_MARKDOWNIT__*/": "markdown-it.min.js",
    "/*__VENDOR_DOMPURIFY__*/": "purify.min.js",
    "/*__VENDOR_HLJS__*/": "highlight.min.js",
    "/*__VENDOR_CYTOSCAPE__*/": "cytoscape.min.js",
}


def inline_vendor(template: str) -> str:
    """Inline the pinned vendored libs at their placeholders. This is build-time
    INJECTION only (no HTML generation). Any literal </script> inside a lib is
    neutralized so it cannot break out of the inline <script> tag — the same
    discipline as the JSON-island < / > escape."""
    for ph, fn in VENDOR_SUBS.items():
        if ph not in template:
            continue
        code = bdv._read(VENDOR_DIR / fn)
        if not code.strip():
            raise SystemExit(f"vendored lib missing or empty: {VENDOR_DIR / fn}")
        code = re.sub(r"</(script)", r"<\\/\1", code, flags=re.I)
        template = template.replace(ph, code)
    return template


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the DeepInit unified report (Docs + Insights).")
    ap.add_argument("output_dir", help="dir containing CLAUDE.md/AGENTS.md + .ai/docs/")
    ap.add_argument("-o", "--out", help="report html path (default <dir>/.ai/report.html)")
    ap.add_argument("--json", action="store_true", help="print the data model JSON to stdout (no html)")
    ap.add_argument("--template", help="override the template path")
    args = ap.parse_args(argv)

    out_dir = Path(args.output_dir)
    if not out_dir.is_dir():
        print(f"error: not a directory: {out_dir}", file=sys.stderr)
        return 2

    model = build_report_model(out_dir)
    if args.json:
        print(json.dumps(model, ensure_ascii=False, indent=2))
        return 0

    here = Path(__file__).resolve().parent.parent
    tpl = Path(args.template) if args.template else here / "skills" / "deep-init" / "assets" / "report-template.html"
    if not tpl.exists():
        print(f"error: template not found: {tpl}", file=sys.stderr)
        return 2

    html = bdv.render(model, inline_vendor(bdv._read(tpl)))
    out_path = Path(args.out) if args.out else (out_dir / ".ai" / "report.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    d = model["dashboard"]
    sev = ", ".join(f"{k}:{v}" for k, v in sorted(d["severity"].items())) or "none"
    print(f"wrote {out_path}  ({len(html):,} bytes; {model['counts']['components']} components, "
          f"{model['counts']['verified_issues']} verified issues [{sev}], "
          f"{model['counts']['adrs']} ADRs, "
          f"risk_metrics={'yes' if d['risk']['available'] else 'unavailable'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
