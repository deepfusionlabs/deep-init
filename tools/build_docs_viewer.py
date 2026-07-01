#!/usr/bin/env python3
"""
build_docs_viewer.py — DeepInit docs-navigation viewer (M7-7)

Turns a deep-init output directory (AGENTS.md + .ai/docs/**) into ONE
self-contained, OFFLINE, vanilla-JS static docs READER (docs-viewer.html).

This is a DOCS READER, not a graph explorer (that stays DeepMap's lane, S-8)
and is a SEPARATE artifact from the issue dashboard (.ai/dashboard.html).

Hard constraints (mirrors the dashboard AF-6 discipline; gated by harness §43):
  * one self-contained .html file — vanilla JS + inline CSS
  * NO CDN / NO network / NO external src|href / no fetch|XHR (opens from file://)
  * license-clean — vendored nothing (the data is the project's own output)
  * content is embedded as an inline JSON island the page JSON.parses
    (file:// CORS forbids fetching a sibling data file, so we inline it)

Usage:
  python tools/build_docs_viewer.py <output_dir> [-o <out.html>]
    <output_dir>  a dir containing AGENTS.md and .ai/docs/ (e.g. a repo root,
                  or a validation/end-to-end/<repo> archive).
    -o            where to write the viewer (default: <output_dir>/.ai/docs-viewer.html)

The parser is deliberately tolerant (R8 graceful degradation): a missing or
oddly-shaped section is skipped, never fatal. It is validated against two real
DeepInit outputs (the kemal end-to-end archive + the oss-kit dogfood archive).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# A file:line (or file:line-line) citation: a path with an extension, then :NN[-NN].
# Tolerates surrounding backticks. Used everywhere we ground a claim.
CITE_RE = re.compile(r"`?([A-Za-z0-9_./\-]+\.[A-Za-z0-9_]+):(\d+(?:-\d+)?)`?")
# A DeepInit record ID: BR- / WF- / IP- / ADR- / KL- / ISS- (+ scoped comp:nnn forms).
ID_RE = re.compile(r"\b((?:BR|WF|IP|ADR|KL|ISS)-[A-Za-z0-9:_\-]+)\b")
PROVENANCE_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _first_prose(md: str) -> str:
    """First non-empty, non-heading, non-comment, non-marker line."""
    for ln in md.splitlines():
        s = ln.strip()
        if not s or s.startswith(("#", "<!--", "-->", "<!", "|", "-", "*", ">")):
            continue
        return s
    return ""


def _strip_markers(md: str) -> str:
    """Drop HTML comments + owned-region markers, keep the human text."""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)
    return md


def _provenance(md: str) -> dict:
    """Pull the R3 provenance fields out of the leading comment block(s)."""
    out: dict[str, str] = {}
    for block in PROVENANCE_RE.findall(md):
        for ln in block.splitlines():
            m = re.match(r"\s*([A-Za-z_]+):\s+(.*?)\s*$", ln)
            if m:
                k, v = m.group(1).lower(), m.group(2).strip()
                if k in ("stage", "run_id", "date", "repo_sha", "component", "inputs") and k not in out:
                    out[k] = v
    return out


def _cites(text: str) -> list[dict]:
    seen, out = set(), []
    for path, line in CITE_RE.findall(text):
        key = f"{path}:{line}"
        if key not in seen:
            seen.add(key)
            out.append({"file": path, "line": line, "ref": key})
    return out


def _ids(text: str) -> list[str]:
    seen, out = set(), []
    for i in ID_RE.findall(text):
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _slug(s: str) -> str:
    """DOM-safe anchor id, prefixed so payload content can never clobber app state."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


# --------------------------------------------------------------------------- #
# AGENTS.md — project identity, architecture, the lean "Critical to know" facts
# --------------------------------------------------------------------------- #
def parse_agents(md: str) -> dict:
    prov = _provenance(md)
    body = _strip_markers(md)

    # title: "# <name> — Agent Context"
    name = ""
    for ln in body.splitlines():
        m = re.match(r"#\s+(.*?)(?:\s+—\s+Agent Context)?\s*$", ln.strip())
        if m and ln.strip().startswith("# "):
            name = m.group(1).replace(" — Agent Context", "").strip()
            break

    tagline = _first_prose(body)

    # Architecture section prose
    architecture = ""
    arch = re.search(r"^##\s+Architecture\s*$(.*?)(?=^##\s)", body, re.M | re.DOTALL)
    if arch:
        architecture = "\n".join(
            l for l in arch.group(1).strip().splitlines() if not l.strip().startswith("-")
        ).strip()

    # Lean facts: bullets under "Critical to know"
    facts: list[dict] = []
    crit = re.search(r"^##\s+Critical to know.*?$(.*?)(?=^##\s|\Z)", body, re.M | re.DOTALL)
    if crit:
        block = crit.group(1)
        # each bullet may span lines until the next "- " at column 0
        for m in re.finditer(r"^-\s+(.*?)(?=^-\s|\Z)", block, re.M | re.DOTALL):
            raw = " ".join(m.group(1).split())
            # skip the italic *Ranked: …* meta-line, but KEEP **bold**-leading facts
            if not raw or (raw.startswith("*") and not raw.startswith("**")):
                continue
            cites = _cites(raw)
            ids = _ids(raw)
            cert = ""
            cm = re.search(r"\[(HIGH|MEDIUM|LOW)\]", raw)
            if cm:
                cert = cm.group(1)
            facts.append({"text": raw, "cites": cites, "ids": ids, "certainty": cert})

    return {
        "name": name,
        "tagline": tagline,
        "architecture": architecture,
        "lean_facts": facts,
        "provenance": prov,
        "lean_md": body.strip(),
    }


# --------------------------------------------------------------------------- #
# Component docs (.ai/docs/components/<name>.md)
# --------------------------------------------------------------------------- #
def parse_component(name: str, md: str) -> dict:
    prov = _provenance(md)
    body = _strip_markers(md)

    role = ""
    rm = re.search(r"\*\*Role\.\*\*\s*(.*?)(?:\n\n|\n##|\Z)", body, re.DOTALL)
    if rm:
        role = " ".join(rm.group(1).split())

    paths: list[str] = []
    pm = re.search(r"\*\*Paths\.\*\*\s*(.*?)(?:\n\n|\n##|\Z)", body, re.DOTALL)
    if pm:
        for path, _ in CITE_RE.findall(pm.group(1)):
            if path not in paths:
                paths.append(path)
        # Paths often listed without :line — grab bare `code` spans too
        for tok in re.findall(r"`([A-Za-z0-9_./\-]+\.[A-Za-z0-9_]+)`", pm.group(1)):
            if tok not in paths:
                paths.append(tok)

    # facts: any bullet OR table-row carrying a record ID + a citation
    # (kemal lists facts as bullets; the dogfood format puts BRs in a table)
    facts: list[dict] = []
    seen_facts: set[str] = set()
    for ln in body.splitlines():
        ids = _ids(ln)
        cites = _cites(ln)
        if not (ids and cites):
            continue
        # normalise: drop leading bullet, collapse table pipes, trim bold markers
        txt = re.sub(r"^\s*[-*|]\s*", "", ln)
        txt = txt.replace("|", " · ").replace("**", "").strip(" ·")
        txt = " ".join(txt.split())
        key = ids[0]
        if key in seen_facts:
            continue
        seen_facts.add(key)
        facts.append({"text": txt, "ids": ids, "cites": cites})

    # cross-component edges (the "Cross-component edges" section bullets)
    edges: list[str] = []
    em = re.search(r"^##\s+Cross-component edges\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.DOTALL)
    if em:
        for m in re.finditer(r"^-\s+(.*?)$", em.group(1), re.M):
            edges.append(" ".join(m.group(1).split()))

    return {
        "name": name,
        "role": role,
        "paths": paths,
        "facts": facts,
        "edges": edges,
        "all_cites": _cites(body),
        "all_ids": _ids(body),
        "body_md": body.strip(),
        "provenance": prov,
    }


# --------------------------------------------------------------------------- #
# decisions.md — ADRs + Knowledge Log + Open Questions
# --------------------------------------------------------------------------- #
def parse_decisions(md: str) -> dict:
    body = _strip_markers(md)
    adrs: list[dict] = []
    # Split on "## ADR-NNNN: Title"
    for m in re.finditer(r"^##\s+(ADR-\d+):\s+(.*?)$(.*?)(?=^##\s|\Z)", body, re.M | re.DOTALL):
        adr_id, title, block = m.group(1), m.group(2).strip(), m.group(3)

        def field(label: str) -> str:
            fm = re.search(rf"-\s+\*\*{label}:\*\*\s*(.*?)(?:\n-\s+\*\*|\Z)", block, re.DOTALL)
            return " ".join(fm.group(1).split()) if fm else ""

        status = field("Status")
        date = field("Date")
        cert = ""
        cm = re.search(r"\[(HIGH|MEDIUM|LOW)\]", field("Certainty") or block)
        if cm:
            cert = cm.group(1)
        adrs.append({
            "id": adr_id,
            "title": title,
            "status": status,
            "date": date,
            "certainty": cert,
            "context": field("Context"),
            "decision": field("Decision"),
            "why": field("Why"),
            "consequences": field("Consequences"),
            "cites": _cites(block),
            "ids": _ids(block),
            "body_md": f"## {adr_id}: {title}\n{block.strip()}",
        })

    # Also accept the dogfood ADR shape DeepInit's OWN ledger emits: "### ADR-N — title"
    # (TRIPLE-hash, em-dash), with "- **Label.**/**Label:**" prose fields. The "ADR-\d+"
    # anchor keeps this from colliding with "### IF-8 —" suppressions or "### KL-…". Idempotent
    # vs the "## ADR-N:" arm above (skip an id already captured). ISS-010: the parser is now the
    # ONE source of truth — build_report.py no longer carries a divergent dup of this.
    _seen_adr = {a["id"] for a in adrs}
    for m in re.finditer(r"^###\s+(ADR-\d+)\s+[—-]\s+(.*?)\s*$(.*?)(?=^###\s|^##\s|\Z)",
                         body, re.M | re.DOTALL):
        adr_id, title, block = m.group(1), m.group(2).strip(), m.group(3)
        if adr_id in _seen_adr:
            continue

        def dfield(label: str) -> str:   # tolerant of "**Label:**" AND "**Label.**"
            fm = re.search(rf"-\s+\*\*{label}[:.]\*\*\s*(.*?)(?=\n-\s+\*\*|\Z)", block, re.DOTALL)
            return " ".join(fm.group(1).split()) if fm else ""

        sm = re.search(r"\*\*Status[:.]\*\*\s*(.*?)(?=\*\*|\n|\Z)", block, re.DOTALL)
        status = " ".join(sm.group(1).split()).strip(" .·") if sm else ""
        cm = re.search(r"\[(HIGH|MEDIUM|LOW)\]", block)
        adrs.append({
            "id": adr_id, "title": title, "status": status, "date": dfield("Date"),
            "certainty": cm.group(1) if cm else "",
            "context": dfield("Context"), "decision": dfield("Decision"),
            "why": dfield("Why"), "consequences": dfield("Consequences"),
            "cites": _cites(block), "ids": _ids(block),
            "body_md": f"### {adr_id} — {title}\n{block.strip()}",
        })

    # Knowledge Log — tolerant of both shapes:
    #   pipe-delimited:  "- **KL-cat:nnn** | text | `file:line` | [CERT]"  (kemal)
    #   em-dash prose:   "- **KL-cat:nnn** — text. `file:line`. [CERT]"   (dogfood)
    kls: list[dict] = []
    kl_sec = re.search(r"^##\s+Knowledge Log.*?$(.*?)(?=^##\s|\Z)", body, re.M | re.DOTALL)
    if kl_sec:
        seen_kl: set[str] = set()
        for ln in kl_sec.group(1).splitlines():
            if "KL-" not in ln:
                continue
            kid = _ids(ln)
            if not kid or kid[0] in seen_kl:
                continue
            seen_kl.add(kid[0])
            cert = ""
            cm = re.search(r"\[(HIGH|MEDIUM|LOW)\]", ln)
            if cm:
                cert = cm.group(1)
            if "|" in ln:
                parts = [p.strip() for p in ln.lstrip("- ").split("|")]
                text = parts[1] if len(parts) > 1 else ""
            else:
                # strip the leading bullet+id, the trailing certainty, and citations
                text = re.sub(r"^\s*[-*]+\s*", "", ln)
                text = re.sub(r"\*\*" + re.escape(kid[0]) + r"\*\*", "", text)
                text = re.sub(r"^\s*[—\-:|]+\s*", "", text)
                text = re.sub(r"\[(HIGH|MEDIUM|LOW)\]\s*$", "", text)
                text = CITE_RE.sub("", text).replace("``", "").replace("**", "")
                text = " ".join(text.split()).strip(" .—-·")
            kls.append({
                "id": kid[0], "text": text, "cites": _cites(ln), "certainty": cert,
            })

    # Open Questions
    oqs: list[str] = []
    oq_sec = re.search(r"^##\s+Open Questions.*?$(.*?)(?=^##\s|\Z)", body, re.M | re.DOTALL)
    if oq_sec:
        for m in re.finditer(r"^-\s+(.*?)$", oq_sec.group(1), re.M):
            oqs.append(" ".join(m.group(1).split()))

    return {"adrs": adrs, "knowledge_log": kls, "open_questions": oqs, "body_md": body.strip()}


# --------------------------------------------------------------------------- #
# issues.md — verified ledger + named suppressions
# --------------------------------------------------------------------------- #
def _bullet_field(block: str, label: str) -> str:
    """Value of a '- **label:** value' bullet (used by the dogfood-shape issue arm)."""
    m = re.search(r"-\s+\*\*" + re.escape(label) + r":\*\*\s*(.*?)(?=\n\s*-\s+\*\*|\Z)", block, re.DOTALL)
    return " ".join(m.group(1).split()) if m else ""


def parse_issues(md: str) -> dict:
    body = _strip_markers(md)
    summary = ""
    sm = re.search(r"\*\*Summary:\*\*\s*(.*?)$", body, re.M)
    if sm:
        summary = " ".join(sm.group(1).split())

    # verified issues — three shapes (all tolerant; the canonical emitted shape is pinned in
    # generation.md "Issue outputs" + issues.md §4.1):
    #   (a) the canonical "## 1. Verified issues" TABLE (kemal e2e);
    #   (b) per-issue "### ISS-<id> — <head>" blocks (H3) ANYWHERE in the body — under "## Fires
    #       (raised)", "## Component: <name>", or a lifecycle heading (the natural per-component
    #       grouping DeepInit emits);
    #   (c) TOP-LEVEL "## ISS-<id> — <title>" blocks (H2) with family/claim/severity bullets.
    verified: list[dict] = []
    vm = re.search(r"##\s+1\.\s+Verified issues(.*?)(?=^##\s|\Z)", body, re.M | re.DOTALL)
    if vm:
        for ln in vm.group(1).splitlines():
            if not ln.strip().startswith("|"):
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) < 5 or cells[0] in ("ISS-id", "—", "") or set("".join(cells)) <= set("-| "):
                continue
            verified.append({
                "id": cells[0], "family": cells[1] if len(cells) > 1 else "",
                "claim": cells[2] if len(cells) > 2 else "", "cites": _cites(ln),
                "severity": cells[4] if len(cells) > 4 else "", "body_md": "",
            })
    # (b) "### ISS-<id> — <head>" blocks, matched ANYWHERE in the body (dogfood 0.7.0 fix). These were
    #     previously matched ONLY inside a "## Fires …" section, so the equally-natural grouping
    #     "### ISS- under ## Component: <name>" (or under a lifecycle heading) parsed as ZERO verified
    #     issues — the report then silently showed "0 issues" while the manifest's issues.counts.open
    #     said otherwise (the exact trust-eroding silent-wrong-output a user hit). Bounded at the next
    #     H3 OR H2 so a block never swallows a sibling section; deduped by id against the (a)/(c) arms.
    _seen_iss = {v["id"] for v in verified}
    for m in re.finditer(r"^###\s+(ISS-[\w:.\-]+)\s+[—-]\s+(.*?)$(.*?)(?=^###\s|^##\s|\Z)",
                         body, re.M | re.DOTALL):
        iid, head, block = m.group(1), m.group(2).strip(), m.group(3)
        if iid in _seen_iss:
            continue
        _seen_iss.add(iid)
        family = _bullet_field(block, "family") or (head.split("—")[0].strip() if "—" in head else "")
        claim = ""
        cm = re.search(r"-\s+\*\*claim:\*\*\s*(.*?)(?:\n-\s+\*\*|\Z)", block, re.DOTALL)
        if cm:
            claim = " ".join(cm.group(1).split())
        sev = ""
        sm2 = re.search(r"-\s+\*\*severity:\*\*\s*(\w+)", block)
        if sm2:
            sev = sm2.group(1)
        if "cosmetic" in family.lower():
            sev = sev or "cosmetic"
        verified.append({
            "id": iid, "family": family, "claim": claim or head,
            "cites": _cites(block), "severity": sev,
            "body_md": f"### {iid} — {head}\n{block.strip()}",
        })
    # (c) DeepInit's OWN emitted ledger shape: TOP-LEVEL "## ISS-NNN — title" blocks with
    #     "- **family/claim/severity:**" bullets. The "ISS-" anchor keeps this from swallowing
    #     "## 1. Verified issues" / "## 2. Named suppressions" / "## Lifecycle …" / "## IF-5 …".
    #     ISS-010: this is the shape build_report.py's removed dup parser handled — now ONE parser.
    for m in re.finditer(r"^##\s+(ISS-[\w:.\-]+)\s+[—-]\s+(.*?)\s*$(.*?)(?=^##\s|\Z)",
                         body, re.M | re.DOTALL):
        iid, title, block = m.group(1), m.group(2).strip(), m.group(3)
        if iid in _seen_iss:
            continue
        _seen_iss.add(iid)
        fam = _bullet_field(block, "family")
        claim = _bullet_field(block, "claim") or title
        sev = _bullet_field(block, "severity")
        sev = sev.split()[0].strip(" .·") if sev else ""
        if "cosmetic" in fam.lower():
            sev = "cosmetic"
        verified.append({
            "id": iid, "family": fam.split()[0] if fam else "", "claim": claim,
            "cites": _cites(block), "severity": sev, "body_md": block.strip(),
        })

    # named suppressions — "### <family> — …" blocks under a "Named suppressions" heading;
    # verdict from **Verdict:** OR the "→ SUPPRESS (…)" tail OR the first bullet line.
    supps: list[dict] = []
    sup_sec = re.search(r"##\s+(?:2\.\s+)?Named suppressions.*?$(.*?)(?=^##\s|\Z)",
                        body, re.M | re.DOTALL)
    if sup_sec:
        for m in re.finditer(r"^###\s+(.*?)$(.*?)(?=^###\s|\Z)", sup_sec.group(1), re.M | re.DOTALL):
            head, block = m.group(1).strip(), m.group(2)
            # family = the leading token before the em-dash/arrow (keep the "-" in "IF-8")
            family = re.split(r"\s+[—–]\s+|\s*→\s*", head)[0].strip()
            verdict = ""
            vd = re.search(r"\*\*Verdict[:\s]*(.*?)\*\*", block)
            if vd:
                verdict = " ".join(vd.group(1).split())
            elif "→" in head:
                verdict = head.split("→", 1)[1].strip()
            else:
                fb = re.search(r"^-\s+(.*?)$", block, re.M)
                if fb:
                    verdict = " ".join(fb.group(1).split())[:160]
            supps.append({
                "family": family, "title": head, "verdict": verdict,
                "cites": _cites(block), "body_md": f"### {head}\n{block.strip()}",
            })

    return {"summary": summary, "verified": verified, "suppressions": supps, "body_md": body.strip()}


# --------------------------------------------------------------------------- #
# Assemble the full data model + derived indexes
# --------------------------------------------------------------------------- #
def build_model(out_dir: Path) -> dict:
    # The lean tier source: AGENTS.md when present (the cross-tool export / the
    # --canonical=agents content file), else the canonical CLAUDE.md (the Claude-Code-native
    # front door DeepInit owns — the "DeepInit owns the front door" model). Both use the same
    # lean format (title + "## Critical to know" facts), so parse_agents handles either.
    lean_path = out_dir / "AGENTS.md"
    if not lean_path.exists():
        lean_path = out_dir / "CLAUDE.md"
    docs = out_dir / ".ai" / "docs"
    comp_dir = docs / "components"

    agents = parse_agents(_read(lean_path)) if lean_path.exists() else {
        "name": out_dir.name, "tagline": "", "architecture": "", "lean_facts": [],
        "provenance": {}, "lean_md": "",
    }

    components: list[dict] = []
    if comp_dir.is_dir():
        for cp in sorted(comp_dir.glob("*.md")):
            components.append(parse_component(cp.stem, _read(cp)))

    decisions = parse_decisions(_read(docs / "decisions.md")) if (docs / "decisions.md").exists() else {
        "adrs": [], "knowledge_log": [], "open_questions": [], "body_md": ""}
    issues = parse_issues(_read(docs / "issues.md")) if (docs / "issues.md").exists() else {
        "summary": "", "verified": [], "suppressions": [], "body_md": ""}

    manifest = {}
    mf = docs / "manifest.json"
    if mf.exists():
        try:
            manifest = json.loads(_read(mf))
        except Exception:
            manifest = {}

    # criticality + file lists from the manifest, keyed by component name
    crit_map: dict[str, dict] = {}
    for cname, cmeta in (manifest.get("components") or {}).items():
        crit_map[cname] = cmeta
    for c in components:
        meta = crit_map.get(c["name"], {})
        c["manifest_files"] = meta.get("files", [])
        c["content_hash"] = meta.get("content_hash", "")
        c["anchor"] = "c-" + _slug(c["name"])
        for fact in c["facts"]:
            fact["anchor"] = _slug(fact["ids"][0]) if fact.get("ids") else ""
    for i, fact in enumerate(agents["lean_facts"]):
        fact["anchor"] = _slug(fact["ids"][0]) if fact.get("ids") else f"lean-{i}"
    for adr in decisions["adrs"]:
        adr["anchor"] = _slug(adr["id"])
    for kl in decisions["knowledge_log"]:
        kl["anchor"] = _slug(kl["id"])
    for i, iss in enumerate(issues["verified"]):
        iss["anchor"] = _slug(iss.get("id") or f"iss-{i}")

    # ----- derived: files index (every cited file → who references it) -----
    files: dict[str, dict] = {}

    def _touch(ref: dict, kind: str, owner: str, label: str):
        f = ref["file"]
        rec = files.setdefault(f, {"file": f, "refs": []})
        rec["refs"].append({"line": ref["line"], "kind": kind, "owner": owner, "label": label})

    for fact in agents["lean_facts"]:
        for ref in fact["cites"]:
            _touch(ref, "lean", "AGENTS.md", fact["text"][:90])
    for c in components:
        for fact in c["facts"]:
            for ref in fact["cites"]:
                _touch(ref, "component", c["name"], fact["text"][:90])
    for adr in decisions["adrs"]:
        for ref in adr["cites"]:
            _touch(ref, "decision", adr["id"], adr["title"])
    for kl in decisions["knowledge_log"]:
        for ref in kl["cites"]:
            _touch(ref, "knowledge", kl["id"], kl["text"][:90])

    files_index = sorted(files.values(), key=lambda r: r["file"])

    # ----- derived: cross-reference map (ID → anchor where it is defined) -----
    # Drives [BR-]/[WF-]/[ADR-]/[KL-]/[ISS-] in-doc links; an ID NOT in here renders
    # as plain text (R1 honesty — never a dead link).
    xref: dict[str, dict] = {}
    for c in components:
        for fact in c["facts"]:
            for i in fact["ids"]:
                if i.startswith(("BR-", "WF-", "IP-")):
                    xref.setdefault(i, {"id": i, "kind": "record", "owner": c["name"],
                                        "anchor": fact.get("anchor") or c["anchor"]})
    for adr in decisions["adrs"]:
        xref[adr["id"]] = {"id": adr["id"], "kind": "decision", "owner": "decisions",
                           "anchor": adr["anchor"]}
    for kl in decisions["knowledge_log"]:
        xref[kl["id"]] = {"id": kl["id"], "kind": "knowledge", "owner": "decisions",
                          "anchor": kl["anchor"]}
    for iss in issues["verified"]:
        if iss.get("id"):
            xref[iss["id"]] = {"id": iss["id"], "kind": "issue", "owner": "issues",
                               "anchor": iss["anchor"]}

    # ----- derived: pre-flattened search index (runtime never re-walks the corpus) -----
    def _plain(md: str) -> str:
        t = re.sub(r"`{1,3}", "", md)
        t = re.sub(r"[#>*_|]", " ", t)
        return " ".join(t.split())

    search_index: list[dict] = []
    search_index.append({"id": "overview", "type": "overview", "title": "Architecture overview",
                         "text": _plain(agents["architecture"] + " " + agents["tagline"]),
                         "view": "overview", "anchor": "overview"})
    for fact in agents["lean_facts"]:
        search_index.append({"id": (fact.get("ids") or [""])[0] or "lean", "type": "fact",
                             "title": "Critical fact", "text": _plain(fact["text"]),
                             "view": "overview", "anchor": fact["anchor"]})
    for c in components:
        search_index.append({"id": c["name"], "type": "component", "title": c["name"],
                             "text": _plain(c["role"] + " " + c["body_md"]),
                             "view": "component", "target": c["name"], "anchor": c["anchor"]})
    for adr in decisions["adrs"]:
        search_index.append({"id": adr["id"], "type": "decision", "title": f'{adr["id"]} · {adr["title"]}',
                             "text": _plain(" ".join([adr["context"], adr["decision"], adr["why"]])),
                             "view": "decisions", "anchor": adr["anchor"]})
    for kl in decisions["knowledge_log"]:
        search_index.append({"id": kl["id"], "type": "knowledge", "title": kl["id"],
                             "text": _plain(kl["text"]), "view": "decisions", "anchor": kl["anchor"]})
    for iss in issues["verified"]:
        search_index.append({"id": iss.get("id", "issue"), "type": "issue",
                             "title": f'{iss.get("id","")} · {iss.get("family","")}',
                             "text": _plain(iss.get("claim", "")), "view": "issues", "anchor": iss["anchor"]})
    for s in issues["suppressions"]:
        search_index.append({"id": s["family"], "type": "suppression",
                             "title": f'{s["family"]} suppression',
                             "text": _plain(s["verdict"]), "view": "issues", "anchor": "suppressions"})

    # headline counts reflect what the viewer ACTUALLY displays (parsed lengths),
    # so the header chips never disagree with the lists below them. The manifest's
    # own authoritative counts are shown verbatim in the Run-manifest panel.
    counts = {
        "components": len(components),
        "lean_facts": len(agents["lean_facts"]),
        "adrs": len(decisions["adrs"]),
        "knowledge_log_entries": len(decisions["knowledge_log"]),
        "verified_issues": len(issues["verified"]),
        "named_suppressions": len(issues["suppressions"]),
        "files_cited": len(files_index),
    }

    repo = manifest.get("repo", {})
    project = {
        "name": agents["name"] or repo.get("name") or out_dir.name,
        "tagline": agents["tagline"],
        "architecture": agents["architecture"],
        "repo_sha": repo.get("pinned_sha") or agents["provenance"].get("repo_sha", ""),
        "source_root": repo.get("source_root", ""),
        "run_id": manifest.get("run_id") or agents["provenance"].get("run_id", ""),
        "generated": manifest.get("generated") or agents["provenance"].get("date", ""),
        "deepinit_version": manifest.get("deepinit_version", ""),
    }

    return {
        "schema": "docs-viewer/v1",
        "project": project,
        "counts": counts,
        "lean_facts": agents["lean_facts"],
        "lean_md": agents["lean_md"],
        "components": components,
        "decisions": decisions["adrs"],
        "knowledge_log": decisions["knowledge_log"],
        "open_questions": decisions["open_questions"],
        "issues": issues,
        "files_index": files_index,
        "xref": xref,
        "search_index": search_index,
        "manifest": manifest,
    }


# --------------------------------------------------------------------------- #
# Render — inject the JSON island into the self-contained template
# --------------------------------------------------------------------------- #
DATA_PLACEHOLDER = "/*__DEEPINIT_VIEWER_DATA__*/"


def render(model: dict, template: str) -> str:
    # JSON embedded inside a <script type="application/json"> island, read via
    # JSON.parse(textContent) — never eval, never fetch. We escape every "<" and
    # ">" to \uXXXX so NO substring of any analyzed-repo snippet in the corpus
    # (a literal "</script>", "<!--", "<svg…>", etc.) can break out of the tag
    # context. JSON.parse restores them transparently. This is the single
    # load-bearing must-do of the embed step (the React/Redux serialize-javascript
    # convention) — and the harness §43 gate enforces it. (U+2028/U+2029 need no
    # escaping here: that hazard is specific to JSON inside a JS STRING literal,
    # not a type="application/json" island read via textContent.)
    blob = json.dumps(model, ensure_ascii=False, separators=(",", ":"))
    lt = chr(92) + "u003c"; gt = chr(92) + "u003e"  # the 6-char strings < / >
    blob = blob.replace("<", lt).replace(">", gt)
    if DATA_PLACEHOLDER not in template:
        raise SystemExit(f"template missing placeholder {DATA_PLACEHOLDER!r}")
    return template.replace(DATA_PLACEHOLDER, blob)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the DeepInit self-contained docs viewer.")
    ap.add_argument("output_dir", help="dir containing AGENTS.md + .ai/docs/")
    ap.add_argument("-o", "--out", help="viewer html path (default <dir>/.ai/docs-viewer.html)")
    ap.add_argument("--json", action="store_true", help="print the data model JSON to stdout (no html)")
    ap.add_argument("--template", help="override the template path")
    args = ap.parse_args(argv)

    out_dir = Path(args.output_dir)
    if not out_dir.is_dir():
        print(f"error: not a directory: {out_dir}", file=sys.stderr)
        return 2

    model = build_model(out_dir)

    if args.json:
        print(json.dumps(model, ensure_ascii=False, indent=2))
        return 0

    here = Path(__file__).resolve().parent.parent
    tpl_path = Path(args.template) if args.template else here / "skills" / "deep-init" / "assets" / "docs-viewer-template.html"
    if not tpl_path.exists():
        print(f"error: template not found: {tpl_path}", file=sys.stderr)
        return 2
    html = render(model, _read(tpl_path))

    out_path = Path(args.out) if args.out else (out_dir / ".ai" / "docs-viewer.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path}  ({len(html):,} bytes; {model['counts']['components']} components, "
          f"{model['counts']['lean_facts']} lean facts, {model['counts']['adrs']} ADRs, "
          f"{model['counts']['files_cited']} files cited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
