#!/usr/bin/env python3
"""build_matrix_manifest.py — DeepInit Phase-6 M1: the deterministic language x size matrix.

Measures every matrix repo with NO LLM: scc (LOC / file_count / per-language / size_tier) +
Graphify (AST node/edge counts + parseable y/n on the DESIGNED structural path) + the pinned SHA.
The output (`validation/matrix/_manifest.json`) is the deterministic substrate the M1 full-pipeline
runs and the M2 cost model build on — it lets the (language x size) grid be DISCOVERED by measurement
rather than pre-assigned, and records whether each cell runs on Graphify (the designed path) or the
grep/ctags fallback.

Separation of duties: this tool measures STRUCTURE + SIZE only (deterministic, reproducible). The
LLM pipeline cost/quality numbers come later, per-repo, into `validation/cost/*.json`.

Size tiers (loc, scc, primary-language-aware whole-repo code total):
  S < 10k  |  M 10k-100k  |  L > 100k

Usage:
  python tools/build_matrix_manifest.py            # measure all clones in REPOS, write the manifest
  python tools/build_matrix_manifest.py --no-graphify   # scc + SHA only (skip the slow AST pass)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLONES = ROOT / "validation" / "_clones"
OUT = ROOT / "validation" / "matrix" / "_manifest.json"

GRAPHIFY = Path(
    os.environ.get("GRAPHIFY_BIN")          # explicit override, if set
    or shutil.which("graphify")             # resolve from PATH (portable)
    or shutil.which("graphify.exe")
    or "graphify"                           # bare name; .exists() False off-PATH -> graceful skip (:112)
)

# clone_dir -> (owner/name, the dominant language we care about for the cell)
REPOS = {
    "click": ("pallets/click", "Python"),
    "gin": ("gin-gonic/gin", "Go"),
    "sinatra": ("sinatra/sinatra", "Ruby"),
    "express": ("expressjs/express", "JavaScript"),
    "gorilla-mux": ("gorilla/mux", "Go"),          # small S-tier Go
    "itsdangerous": ("pallets/itsdangerous", "Python"),  # small S-tier Python
    "phoenix": ("phoenixframework/phoenix", "Elixir"),
    "fmt": ("fmtlib/fmt", "C++"),
    "redis": ("redis/redis", "C"),
    "laravel-framework": ("laravel/framework", "PHP"),
    # reused clones (already measured for Mirror/sweeps; folded into the matrix)
    "excalidraw": ("excalidraw/excalidraw", "TypeScript"),
    "pyccel": ("pyccel/pyccel", "Python"),
    "uniffi-rs": ("mozilla/uniffi-rs", "Rust"),
    "kotlinx-schema": ("Kotlin/kotlinx-serialization-json-schema", "Kotlin"),
    "commercetools-sync-java": ("commercetools/commercetools-sync-java", "Java"),
    "kemal": ("kemalcr/kemal", "Crystal"),
}

# scc rolls these up but they are not "source" for component/extraction purposes
NON_SOURCE = {"Markdown", "YAML", "JSON", "Plain Text", "License", "TOML", "INI",
              "gitignore", "Makefile", "Batch", "Shell", "HTML", "CSS", "SVG",
              "XML", "Protocol Buffers", "Docker ignore", "Dockerfile", "BASH",
              "Autoconf", "m4", "Bourne Shell", "Properties File", "Patch",
              "ReStructuredText", "Org", "AsciiDoc", "Jupyter"}


# dirs that are NOT repo source for sizing: our own measurement artifact + the standard
# vendor/generated/build trees the skill's exclusion pass (detection.md §37) also skips.
EXCLUDE_DIRS = "graphify-out,node_modules,vendor,dist,build,target,__pycache__,.git,.venv,out,bin,obj"


def tier(loc: int) -> str:
    if loc < 10_000:
        return "S"
    if loc <= 100_000:
        return "M"
    return "L"


def run_scc(path: Path) -> dict | None:
    try:
        out = subprocess.run(["scc", "--format", "json", "--exclude-dir", EXCLUDE_DIRS, str(path)],
                             capture_output=True, text=True, timeout=300)
        data = json.loads(out.stdout)
    except Exception as e:  # noqa: BLE001
        print(f"  scc failed on {path.name}: {e}", file=sys.stderr)
        return None
    langs = sorted(({"lang": r["Name"], "loc": r["Code"], "files": r["Count"]}
                   for r in data), key=lambda r: -r["loc"])
    total_loc = sum(l["loc"] for l in langs)
    total_files = sum(l["files"] for l in langs)
    source_loc = sum(l["loc"] for l in langs if l["lang"] not in NON_SOURCE)
    primary = langs[0] if langs else None
    return {
        "loc": total_loc, "file_count": total_files, "source_loc": source_loc,
        "languages": [{"lang": l["lang"], "loc": l["loc"],
                       "pct": round(100 * l["loc"] / total_loc, 1) if total_loc else 0.0}
                      for l in langs[:8]],
        "primary_language": {"lang": primary["lang"], "loc": primary["loc"],
                             "file_count": primary["files"],
                             "pct": round(100 * primary["loc"] / total_loc, 1) if total_loc else 0.0}
        if primary else None,
        # tier on CODE size (source_loc excludes JSON/data/markup), not total-incl-data —
        # otherwise a repo with big committed JSON fixtures mis-tiers as larger than it is.
        "size_tier": tier(source_loc),
        "size_basis": "source_loc (code only; data/markup excluded)",
    }


def run_graphify(path: Path, reuse: bool = True) -> dict:
    gj = path / "graphify-out" / "graph.json"
    if not GRAPHIFY.exists():
        return {"parseable": None, "reason": "graphify CLI not found"}
    if not (reuse and gj.exists()):
        try:
            subprocess.run([str(GRAPHIFY), "update", str(path), "--no-cluster"],
                           capture_output=True, text=True, timeout=900)
        except Exception as e:  # noqa: BLE001
            return {"parseable": False, "reason": f"graphify run failed: {e}"}
    if not gj.exists():
        return {"parseable": False, "reason": "no graph.json emitted"}
    try:
        d = json.loads(gj.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"parseable": False, "reason": f"graph.json unreadable: {e}"}
    nodes = d.get("nodes") or []
    links = d.get("links") or []
    ast_nodes = [n for n in nodes if n.get("_origin") == "ast"]
    # "parseable on the DESIGNED path" must mean the repo's SOURCE was parsed — not just its
    # docs/data. A no-grammar stack (e.g. Crystal) still yields AST nodes for its .md/.json files;
    # that is NOT a code parse. Count only AST nodes whose source file is a code (non-doc/data) file.
    DOC_DATA = (".md", ".json", ".yaml", ".yml", ".txt", ".rst", ".toml", ".cfg", ".ini", ".lock", ".csv", ".xml", ".html")
    source_ast = [n for n in ast_nodes if not (n.get("source_file", "").lower().endswith(DOC_DATA))]
    import_edges = [l for l in links if l.get("relation") == "imports_from"]
    return {
        "parseable": len(source_ast) > 0,          # source (code) was parsed, not just docs/data
        "nodes": len(nodes), "ast_nodes": len(ast_nodes), "source_ast_nodes": len(source_ast),
        "edges": len(links), "import_edges": len(import_edges),
    }


def git_sha(path: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=30).stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-graphify", action="store_true")
    ap.add_argument("--only", help="comma-separated clone dirs to (re)measure")
    args = ap.parse_args(argv)

    only = set(args.only.split(",")) if args.only else None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"repos": {}}
    repos = existing.get("repos", {})

    for clone_dir, (owner_name, dom_lang) in REPOS.items():
        if only and clone_dir not in only:
            continue
        path = CLONES / clone_dir
        if not path.exists():
            print(f"SKIP {clone_dir} (not cloned)")
            continue
        print(f"measuring {clone_dir} ({owner_name}) ...")
        scc = run_scc(path)
        if scc is None:
            continue
        gfy = {"parseable": None, "reason": "skipped"} if args.no_graphify else run_graphify(path)
        repos[clone_dir] = {
            "repo": owner_name, "dominant_language": dom_lang,
            "pinned_sha": git_sha(path), "clone_depth": "shallow",
            **scc, "graphify": gfy,
        }
        g = repos[clone_dir]
        print(f"  {scc['size_tier']}  loc={scc['loc']:>7}  files={scc['file_count']:>4}  "
              f"primary={scc['primary_language']['lang'] if scc['primary_language'] else '?'}  "
              f"graphify={'parse' if gfy.get('parseable') else 'fallback'}"
              + (f" ({gfy.get('ast_nodes')} ast nodes)" if gfy.get('parseable') else ""))

    # roll up the grid
    grid = {}
    for k, v in repos.items():
        grid.setdefault(v["dominant_language"], {}).setdefault(v["size_tier"], []).append(k)
    out = {
        "schema": "deepinit-validation/matrix-manifest/v1",
        "note": "Deterministic language x size matrix. scc (size/langs/tier) + Graphify (AST parseability) "
                "+ pinned SHA. No LLM. The substrate for the M1 full-pipeline runs + the M2 cost model.",
        "size_tiers": {"S": "<10k loc", "M": "10k-100k loc", "L": ">100k loc"},
        "grid": {lang: {t: sorted(grid[lang][t]) for t in sorted(grid[lang])} for lang in sorted(grid)},
        "graphify_parseable_count": sum(1 for v in repos.values() if v["graphify"].get("parseable")),
        "repo_count": len(repos),
        "repos": dict(sorted(repos.items())),
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(repos)} repos, "
          f"{out['graphify_parseable_count']} Graphify-parseable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
