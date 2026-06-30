#!/usr/bin/env python3
"""graphify_adapter.py — DeepInit Layer-3 structural adapter.

Deterministic, no-LLM, no-network reference implementation of detection.md's
"`graph.json` -> `structural-graph.json`" mapping. This is the bridge between
Graphify's real output (`graphify update <path> --no-cluster` ->
`graphify-out/graph.json`, nodes + links) and the component-keyed
`structural-graph.json` shape the downstream detectors consume
(component registry / dependency-edge / IF-8 cycle / IF-3a coupling).

Why a reference tool (the project is otherwise instruction-defined):
  - it makes the Layer-3 mapping TESTABLE + reproducible (a harness gate),
  - it lets the A/B "designed path vs grep fallback" validation run deterministically,
  - automation > a manual step (objective hierarchy #2).
The in-skill prose in detection.md remains the spec; this is its executable form.

Graphify graph.json contract (observed, v0.8.39):
  nodes[]: {id, label, source_file, source_location ("L<n>"), file_type, _origin}
  links[]: {source, target, relation, context, source_file, source_location, weight, ...}
    relation in {contains, imports, imports_from, extends, calls, ...}
    context == "import" marks a cross-file import edge.
    A link target that is NOT a node id is an EXTERNAL package (unresolved) -> a third-party dep.
    A link target that IS a node id resolves to that node's source_file (an internal edge).

structural-graph.json (v2) cross-component edge classes, each {comp: [symbols]}:
    imports_from / imported_by   <- import edges (context "import" / imports|imports_from|uses|depends_on)
    calls_into   / called_by     <- runtime call edges (context "call" / relation calls)            [NEW v2]
    inherits_from/ inherited_by  <- inheritance edges (inherits|extends|implements|mixes_in|includes) [NEW v2]
  The import skeleton (files/exports/imports_from/imported_by/external_dependencies) is
  BYTE-IDENTICAL to v1; the call/inherit classes are additive and empty {} under the grep
  fallback. detect_cycles stays import-only; classify_cycles uses calls_into for the IF-8
  type-vs-value (runtime-vs-type-only) cycle distinction detection.md's Layer-3 spec asks for.

Component mapping: each source_file -> a component by LONGEST-PREFIX match against a
registry ({component: [path_prefix, ...]}). With no registry, components are derived by
grouping source files at a configurable path depth (monorepo `packages/<name>` etc.).
Files that map to no component (data/config/vendored) are excluded from the skeleton.

Usage:
  python tools/graphify_adapter.py --graph graphify-out/graph.json --out structural-graph.json
  python tools/graphify_adapter.py --graph g.json --registry registry.json --out sg.json
  python tools/graphify_adapter.py --graph g.json --component-depth 2 --src-prefix packages --out sg.json

Exit 0 on success; non-zero on a malformed graph (never silently emits a wrong skeleton).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

# Import edges Graphify emits. context=="import" is the authoritative marker, but we also
# accept relation in this set for robustness against missing context tags.
_IMPORT_RELATIONS = {"imports", "imports_from", "uses", "depends_on"}

# Runtime CALL edges (context=="call"). These were dropped before — yet detection.md's
# Layer-3 spec already relies on the `calls` relation as the POSITIVE runtime-use signal
# for the IF-8 type-vs-value cycle distinction. Captured as a SEPARATE edge class
# (calls_into / called_by) — NOT merged into imports_from, so the import skeleton and every
# existing consumer/gate stay byte-identical. (Measured: `calls` is the single largest
# relation Graphify emits — ~93k edges across the validation corpus — and 100% discarded.)
_CALL_RELATIONS = {"calls"}

# Inheritance / mixin edges. `extends` already arrives with context=="import" (so it is
# ALSO counted as an import, unchanged); the rest (inherits/implements/mixes_in/includes)
# were dropped. Captured as a second class (inherits_from / inherited_by).
_INHERIT_RELATIONS = {"inherits", "extends", "implements", "mixes_in", "includes"}

# Source-file suffixes Graphify can parse but that are NOT first-class code components for
# the structural skeleton (manifests / data) — excluded only when no registry assigns them.
_NON_CODE_SUFFIXES = (".json", ".lock", ".md", ".txt", ".yml", ".yaml", ".toml", ".cfg", ".ini")


def _norm(path: str) -> str:
    """Normalise a graphify source_file to forward-slash, no leading ./"""
    if path is None:
        return ""
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def load_graph(graph_path: str) -> dict:
    with open(graph_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("graph.json root must be an object")
    if "nodes" not in data:
        raise ValueError("graph.json missing 'nodes'")
    # graphify uses 'links'; tolerate 'edges' too.
    if "links" not in data and "edges" not in data:
        raise ValueError("graph.json missing 'links'/'edges'")
    return data


def _links(data: dict) -> list:
    return data.get("links") or data.get("edges") or []


def assign_component(source_file: str, registry: dict | None, depth: int, src_prefix: str | None) -> str | None:
    """Map a source file to a component name.

    With a registry: longest-prefix match against its path lists.
    Without: group by the path segment at `depth` (optionally under `src_prefix`).
    Returns None when the file belongs to no component (excluded from the skeleton).
    """
    sf = _norm(source_file)
    if not sf:
        return None
    if registry:
        best_comp, best_len = None, -1
        for comp, prefixes in registry.items():
            for pre in prefixes:
                pre_n = _norm(pre).rstrip("/")
                if sf == pre_n or sf.startswith(pre_n + "/"):
                    if len(pre_n) > best_len:
                        best_comp, best_len = comp, len(pre_n)
        return best_comp
    # Derivation mode (no registry).
    parts = sf.split("/")
    if src_prefix:
        sp = _norm(src_prefix).strip("/")
        # find the src_prefix segment, take the next `depth` segments as the component key
        try:
            idx = parts.index(sp)
        except ValueError:
            return None
        comp_parts = parts[idx + 1 : idx + 1 + depth]
        if not comp_parts:
            return None
        # drop a trailing filename if the prefix is shallow
        return "/".join(comp_parts)
    # plain depth grouping from repo root
    if len(parts) <= depth:
        # file sits above the grouping depth -> use its parent dir (or 'root')
        return parts[0] if len(parts) > 1 else "root"
    return "/".join(parts[:depth])


def build_structural_graph(
    data: dict,
    registry: dict | None = None,
    depth: int = 1,
    src_prefix: str | None = None,
    exclude_non_code: bool = True,
) -> dict:
    nodes = data.get("nodes", [])
    node_by_id = {n["id"]: n for n in nodes if "id" in n}

    # file -> component, with non-code exclusion when no registry claims the file.
    def file_component(sf: str) -> str | None:
        comp = assign_component(sf, registry, depth, src_prefix)
        if comp is None:
            return None
        if exclude_non_code and registry is None and _norm(sf).endswith(_NON_CODE_SUFFIXES):
            return None
        return comp

    components: dict = defaultdict(
        lambda: {
            "files": set(),
            "exports": set(),
            "imports_from": defaultdict(set),
            "imported_by": defaultdict(set),
            "calls_into": defaultdict(set),
            "called_by": defaultdict(set),
            "inherits_from": defaultdict(set),
            "inherited_by": defaultdict(set),
        }
    )
    external_deps: dict = defaultdict(set)  # component -> {external package names}

    # Register every node's file under its component.
    for n in nodes:
        sf = _norm(n.get("source_file", ""))
        comp = file_component(sf)
        if comp is None:
            continue
        components[comp]["files"].add(sf)

    # Resolve cross-component edges. Imports populate imports_from/imported_by/exports
    # EXACTLY as before (byte-stable); calls and inheritance populate their own parallel
    # edge classes, so the import skeleton — and every existing consumer/gate — is unchanged.
    for link in _links(data):
        ctx = link.get("context")
        rel = link.get("relation")
        is_import = ctx == "import" or rel in _IMPORT_RELATIONS
        is_call = ctx == "call" or rel in _CALL_RELATIONS
        is_inherit = rel in _INHERIT_RELATIONS
        if not (is_import or is_call or is_inherit):
            continue
        src_node = node_by_id.get(link.get("source"))
        if src_node is None:
            continue
        src_file = _norm(src_node.get("source_file", ""))
        src_comp = file_component(src_file)
        if src_comp is None:
            continue
        tgt_id = link.get("target")
        tgt_node = node_by_id.get(tgt_id)
        symbol = (tgt_node.get("label") if tgt_node else tgt_id) or tgt_id
        if tgt_node is None:
            # unresolved target -> external third-party package (IMPORT semantics only; an
            # unresolved call/inherit target is a stdlib/builtin, not a component edge)
            if is_import:
                external_deps[src_comp].add(str(tgt_id))
            continue
        tgt_file = _norm(tgt_node.get("source_file", ""))
        tgt_comp = file_component(tgt_file)
        if tgt_comp is None:
            if is_import:
                external_deps[src_comp].add(str(symbol))
            continue
        if tgt_comp == src_comp:
            continue  # intra-component edge: not a cross-component dependency
        if is_import:
            components[src_comp]["imports_from"][tgt_comp].add(str(symbol))
            components[tgt_comp]["imported_by"][src_comp].add(str(symbol))
            components[tgt_comp]["exports"].add(str(symbol))  # imported across a boundary => public surface
        if is_call:
            components[src_comp]["calls_into"][tgt_comp].add(str(symbol))
            components[tgt_comp]["called_by"][src_comp].add(str(symbol))
        if is_inherit:
            components[src_comp]["inherits_from"][tgt_comp].add(str(symbol))
            components[tgt_comp]["inherited_by"][src_comp].add(str(symbol))

    # Freeze to JSON-serialisable, sorted shapes (byte-stable output).
    out_components = {}
    for comp in sorted(components):
        c = components[comp]
        out_components[comp] = {
            "files": sorted(c["files"]),
            "exports": sorted(c["exports"]),
            "imports_from": {k: sorted(v) for k, v in sorted(c["imports_from"].items())},
            "imported_by": {k: sorted(v) for k, v in sorted(c["imported_by"].items())},
            "calls_into": {k: sorted(v) for k, v in sorted(c["calls_into"].items())},
            "called_by": {k: sorted(v) for k, v in sorted(c["called_by"].items())},
            "inherits_from": {k: sorted(v) for k, v in sorted(c["inherits_from"].items())},
            "inherited_by": {k: sorted(v) for k, v in sorted(c["inherited_by"].items())},
        }

    result = {
        "version": 2,  # v2: + calls_into/called_by + inherits_from/inherited_by (import fields byte-identical to v1)
        "source": "graphify",
        "generated_by": "tools/graphify_adapter.py",
        "components": out_components,
    }
    if any(external_deps.values()):
        result["external_dependencies"] = {
            k: sorted(v) for k, v in sorted(external_deps.items()) if v
        }
    return result


def detect_cycles(structural_graph: dict) -> list:
    """Tarjan SCC over the cross-component import graph; return SCCs of size > 1
    (and self-loops). This is the IF-8 substrate — returned for the A/B validation,
    not part of the structural-graph.json contract."""
    comps = structural_graph["components"]
    adj = {c: set(comps[c]["imports_from"].keys()) for c in comps}
    index_counter = [0]
    stack: list = []
    on_stack: dict = {}
    index: dict = {}
    lowlink: dict = {}
    sccs: list = []

    import sys as _sys

    _sys.setrecursionlimit(10000)

    def strongconnect(v):
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in sorted(adj.get(v, ())):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w):
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            comp_scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                comp_scc.append(w)
                if w == v:
                    break
            sccs.append(sorted(comp_scc))

    for v in sorted(adj):
        if v not in index:
            strongconnect(v)
    # size>1, or a self-loop
    cycles = [s for s in sccs if len(s) > 1]
    for v in adj:
        if v in adj.get(v, ()):  # self-import edge
            cycles.append([v])
    return sorted(cycles)


def classify_cycles(structural_graph: dict) -> list:
    """IF-8 type-vs-value suppression substrate (resolves detection.md Layer-3's :47 note).

    Each import-graph SCC (detect_cycles) is tagged `runtime_backed`: True iff at least one
    cross-member edge is a real runtime `calls_into` edge (a VALUE use), else the cycle rests
    only on imports — which on TS/Java/etc. are often compile-erased type-only imports that
    inflate the SCC. The skill-layer IF-8 detector keeps the runtime-backed cycles and
    downgrades/suppresses the type-only-suspect ones, so the `calls` signal the spec relies
    on finally reaches the detector. Pure function over the v2 structural graph; with empty
    calls maps (grep fallback / v1 graph) every cycle is runtime_backed=False — an honest
    'unconfirmed', never a false suppression of a real import cycle."""
    comps = (structural_graph or {}).get("components", {}) or {}
    out = []
    for members in detect_cycles(structural_graph):
        mset = set(members)
        runtime_backed = False
        for m in members:
            calls = (comps.get(m, {}) or {}).get("calls_into", {}) or {}
            if any(t in mset and t != m for t in calls):
                runtime_backed = True
                break
        out.append({"members": members, "runtime_backed": runtime_backed})
    return sorted(out, key=lambda d: d["members"])


def symbol_dependents(structural_graph: dict, component: str, symbol: str) -> list:
    """DP-1 symbol-level narrowing (Tier-4): the components that actually depend on a
    SPECIFIC exported `symbol` of `component` — those whose imports_from / calls_into /
    inherits_from edge TO `component` lists that symbol. Lets `--update` re-mark only the
    real dependents of a CHANGED symbol dirty, instead of the whole `imported_by` closure
    (fewer false-clean skips on a behavioural change AND fewer needless re-analyses when an
    UNRELATED symbol of the same component changed). Symbol-precise only where the v2 edge
    lists carry the symbol; the caller falls back to the full `imported_by` closure when the
    edge is coarse (wildcard/namespace import with no symbol list, or the grep fallback), and
    horizontal (update.md Step 4) stays the safety net — so narrowing is precision-only and
    never drops a real dependent."""
    comps = (structural_graph or {}).get("components", {}) or {}
    deps = set()
    for name, c in comps.items():
        if name == component or not isinstance(c, dict):
            continue
        for cls in ("imports_from", "calls_into", "inherits_from"):
            if symbol in ((c.get(cls) or {}).get(component) or []):
                deps.add(name)
                break
    return sorted(deps)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Graphify graph.json -> DeepInit structural-graph.json adapter")
    ap.add_argument("--graph", required=True, help="path to graphify-out/graph.json")
    ap.add_argument("--out", help="output structural-graph.json path (default: stdout)")
    ap.add_argument("--registry", help="optional JSON {component: [path_prefix,...]} for longest-prefix mapping")
    ap.add_argument("--component-depth", type=int, default=1, help="path depth for component derivation when no registry (default 1)")
    ap.add_argument("--src-prefix", help="only group files under this path segment (e.g. 'packages' for a monorepo)")
    ap.add_argument("--cycles", action="store_true", help="also print detected cross-component cycles (IF-8 substrate) to stderr")
    args = ap.parse_args(argv)

    try:
        data = load_graph(args.graph)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot load graph: {e}", file=sys.stderr)
        return 2

    registry = None
    if args.registry:
        with open(args.registry, "r", encoding="utf-8") as fh:
            registry = json.load(fh)

    sg = build_structural_graph(data, registry=registry, depth=args.component_depth, src_prefix=args.src_prefix)

    text = json.dumps(sg, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"wrote {args.out}: {len(sg['components'])} components", file=sys.stderr)
    else:
        print(text)

    if args.cycles:
        cycles = detect_cycles(sg)
        if cycles:
            print(f"CYCLES ({len(cycles)}):", file=sys.stderr)
            for c in cycles:
                print("  " + " <-> ".join(c), file=sys.stderr)
        else:
            print("CYCLES: none (DAG)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
