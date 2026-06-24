#!/usr/bin/env python3
"""
build_i18n.py — DeepInit per-language report builder (post-generation overlay).

English `report.html` is the CANONICAL analysis output (build_report.py); it is never
touched. `report.<lang>.html` is a DERIVED overlay built by this PURE function of
(English model, translation memory, lang):

    model  = build_report.build_report_model(out_dir)      # canonical English
    apply_tm(model, tm, lang)                               # translate PROSE fields only
    html   = bdv.render(model, inline_vendor(template))     # same byte-stable render path
    html   = _set_html_lang(html, lang)                     # <html lang dir> (rtl for he)

The LLM (the skill) PRODUCES the translation memory; this builder only CONSUMES it, so
the deterministic / harness-testable boundary is exactly here — no network, no LLM, no
clock, no RNG (the harness pins the output byte-for-byte against a fixture TM).

Grounding is preserved: only human prose is translated, and every entry is gated by
`i18n_tokens.verify` (every `file:line` / record-ID / code / product-noun survives
verbatim) — a miss or a corrupted token HONEST-DEGRADES that field to English (never
blank, never fabricated; R1 / KL-learning:001). Chrome (UI labels) is a static STRINGS
table baked into the template (all langs), picked client-side by the `<html lang>`; this
builder sets that lang/dir and translates the data-island prose.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import build_docs_viewer as bdv  # tolerant parsers + escaped-embed render (one source of truth)
import build_report as br        # the canonical English model + vendored-lib inliner
import i18n_tokens as i18         # grounded-token protect-mask + verify + cache key

# The shipped TARGET languages + the canonical `en` base — the single source of truth for the
# SHIPPED set (the config-schema enum, the template STRINGS table, and the Translate picker all
# mirror this). Trimmed to en + Spanish + Hebrew (the curated/chrome-baked/harness-tested set);
# ANY OTHER language still translates on demand via the `other:<language>` path below (expand-only —
# the capability is intact; only the default shipped surface shrank). `dir` drives RTL: Hebrew is rtl.
LANGS = {
    "en": {"name": "English",          "dir": "ltr"},
    "es": {"name": "Español",          "dir": "ltr"},
    "he": {"name": "עברית",            "dir": "rtl"},
}
TARGET_LANGS = [c for c in LANGS if c != "en"]   # the 2 shipped translation targets (en is the canonical base)

# Known RTL scripts for the on-demand (`other:<language>`) path: chrome honest-degrades to English
# (the template T() falls back), but the page direction still flips for an RTL language.
_RTL_CODES = {"he", "fa", "ar", "ur", "yi", "dv", "ps"}


def _norm_lang(lang) -> str:
    """Normalize a requested language: strip an `other:` prefix and surrounding space. Returns the
    bare code/name as given (the engine maps a picker choice to a short code; on-demand free text
    is accepted verbatim)."""
    s = str(lang or "").strip()
    if s.lower().startswith("other:"):
        s = s.split(":", 1)[1].strip()
    return s


def _lang_meta(lang):
    """(code, name, dir) for a language. A SHIPPED lang uses its curated LANGS row; ANY OTHER
    language is accepted on demand (expand-only) — chrome honest-degrades to English (template T()
    falls back, stated never silent), the page direction flips for a known RTL script, name = the
    code as given. Idempotent (re-normalizing an already-bare code is a no-op)."""
    code = _norm_lang(lang)
    if code in LANGS:
        return code, LANGS[code]["name"], LANGS[code]["dir"]
    return code, code, ("rtl" if code.lower() in _RTL_CODES else "ltr")

# CHROME_KEYS — the curated chrome (UI-label) string keys the template's STRINGS table MUST define
# for EVERY language (the §71 G0 completeness contract). Chrome is fixed UI text translated ONCE and
# shipped in the template (free at build time); per-repo PROSE is the LLM/TM path above.
CHROME_KEYS = [
    "docs", "insights", "overview", "components", "knowledge", "decisions", "issues", "grounding",
    "search_placeholder", "on_this_page", "toggle_theme", "shortcuts",
    "kpi_components", "kpi_open_issues", "kpi_decisions", "kpi_knowledge", "kpi_files_cited", "kpi_critical_facts",
    "card_severity", "card_risk", "card_decisions", "card_drift", "card_graph", "card_triage",
    "map", "map_lead", "map_filter", "map_search", "map_reset", "map_legend",
    "metrics_unavailable", "drift_unavailable", "graph_unavailable", "no_issues_clean",
]


def _tr_factory(tm: dict, lang: str, stats: dict):
    """Return a translate-one-string function: TM lookup keyed by content hash, gated by
    token-integrity verify, honest-degrading to the English source on miss/fail."""
    pv = (tm or {}).get("prompt_version", "")
    gh = (tm or {}).get("glossary_hash", "")
    entries = (tm or {}).get("entries", {}) or {}

    def tr(s):
        if not s or not str(s).strip():
            return s
        e = entries.get(i18.content_key(pv, lang, gh, s))
        if e and isinstance(e.get("translated"), str) and i18.verify(e["translated"], e.get("tokens") or []):
            stats["translated"] += 1
            return e["translated"]
        stats["untranslated"] += 1
        return s   # English fallback — never blank, never fabricated (R1)

    return tr


def apply_tm(model: dict, tm: dict, lang: str) -> dict:
    """Translate the human PROSE fields of the report model in place via the TM; structural
    fields (ids, anchors, cites, paths, hashes, the xref map) are NEVER touched. Records an
    honest `model['i18n']` coverage block. Pure + deterministic (sorted reads, no clock)."""
    stats = {"translated": 0, "untranslated": 0}
    tr = _tr_factory(tm, lang, stats)

    pj = model.get("project") or {}
    for k in ("tagline", "architecture"):   # project name stays verbatim (proper noun)
        if pj.get(k):
            pj[k] = tr(pj[k])
    if model.get("lean_md"):
        model["lean_md"] = tr(model["lean_md"])
    for fct in (model.get("lean_facts") or []):
        if fct.get("text"):
            fct["text"] = tr(fct["text"])
    for c in (model.get("components") or []):
        for k in ("role", "body_md"):
            if c.get(k):
                c[k] = tr(c[k])
        if c.get("edges"):
            c["edges"] = [tr(e) for e in c["edges"]]
    for d in (model.get("decisions") or []):
        for k in ("title", "context", "decision", "why", "consequences", "body_md"):
            if d.get(k):
                d[k] = tr(d[k])
    for kl in (model.get("knowledge_log") or []):
        if kl.get("text"):
            kl["text"] = tr(kl["text"])
    if model.get("open_questions"):
        model["open_questions"] = [tr(q) for q in model["open_questions"]]
    iss = model.get("issues") or {}
    if iss.get("summary"):
        iss["summary"] = tr(iss["summary"])
    for v in (iss.get("verified") or []):
        for k in ("claim", "body_md"):
            if v.get(k):
                v[k] = tr(v[k])
    for s in (iss.get("suppressions") or []):
        for k in ("title", "verdict", "body_md"):
            if s.get(k):
                s[k] = tr(s[k])

    total = stats["translated"] + stats["untranslated"]
    code, name, direction = _lang_meta(lang)
    model["i18n"] = {
        "lang": code, "name": name, "dir": direction,
        "translated": stats["translated"], "untranslated": stats["untranslated"],
        "coverage_pct": (round(100.0 * stats["translated"] / total, 1) if total else 0.0),
    }
    return model


def _set_html_lang(html: str, lang: str, direction: str) -> str:
    """Set <html lang dir> on the single root tag (replacing the template's lang='en')."""
    def repl(m):
        attrs = re.sub(r'\slang="[^"]*"', "", m.group(1))
        attrs = re.sub(r'\sdir="[^"]*"', "", attrs)
        return f'<html lang="{lang}" dir="{direction}"{attrs}>'
    return re.sub(r"<html\b([^>]*)>", repl, html, count=1)


def build(out_dir, lang: str, tm_path=None, template=None, available=None) -> str:
    """Build the self-contained report HTML for `lang` (a PURE function of the inputs).

    `available` (optional) is the ordered list of [{code,name,dir}] sibling reports generated in
    this run; injected into model['i18n']['available'] so the template can render an in-app
    language switcher that navigates between the per-language files.

    A SHIPPED language (en/es/he) builds with its curated chrome; ANY OTHER language builds on
    demand (expand-only) — content prose is still translated from the TM, the page direction flips
    for a known RTL script, and chrome honest-degrades to English via the template's T() fallback."""
    code, name, direction = _lang_meta(lang)
    if not code:
        raise SystemExit(f"no language given (shipped: {', '.join(LANGS)} or other:<language>)")
    out_dir = Path(out_dir)
    model = br.build_report_model(out_dir)
    if code == "en":
        model["i18n"] = {"lang": "en", "name": "English", "dir": "ltr",
                         "translated": 0, "untranslated": 0, "coverage_pct": 100.0}
    else:
        tmp = Path(tm_path) if tm_path else (out_dir / ".ai" / "i18n" / "translation_memory.json")
        tm = {}
        if tmp.exists():
            try:
                tm = json.loads(tmp.read_text(encoding="utf-8"))
            except Exception:
                tm = {}
        apply_tm(model, tm, code)
    if available and len(available) > 1:
        model["i18n"]["available"] = available
    here = Path(__file__).resolve().parent.parent
    tpl = Path(template) if template else here / "skills" / "deep-init" / "assets" / "report-template.html"
    html = bdv.render(model, br.inline_vendor(bdv._read(tpl)))
    return _set_html_lang(html, code, direction)


def _report_filename(lang: str) -> str:
    """The on-disk filename for a language (en is the canonical report.html the switcher anchors on)."""
    return "report.html" if lang == "en" else f"report.{lang}.html"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build a per-language DeepInit report (report.<lang>.html).")
    ap.add_argument("output_dir", help="dir containing CLAUDE.md/AGENTS.md + .ai/docs/")
    ap.add_argument("--lang", required=True, help="language: a shipped code (" + ", ".join(TARGET_LANGS) + "), 'en', 'all', or any other:<language> (on-demand, chrome→English)")
    ap.add_argument("--tm", help="translation-memory path (default <dir>/.ai/i18n/translation_memory.json)")
    ap.add_argument("--template", help="override the template path")
    args = ap.parse_args(argv)

    out_dir = Path(args.output_dir)
    if not out_dir.is_dir():
        print(f"error: not a directory: {out_dir}", file=sys.stderr)
        return 2
    if args.lang == "all":
        requested = list(TARGET_LANGS)
    else:
        requested = [x.strip() for x in args.lang.split(",") if x.strip()]
    # Always anchor on en (report.html) so the in-app switcher has a canonical home; en first, dedup.
    # `other:` prefixes + arbitrary codes are accepted on demand (expand-only); no language is rejected.
    built = []
    for c in (["en"] + requested):
        cc = _norm_lang(c)
        if cc and cc not in built:
            built.append(cc)
    # The set the switcher offers (omitted when only one report is built — nothing to switch to).
    available = [dict(zip(("code", "name", "dir"), _lang_meta(c))) for c in built]
    for lang in built:
        html = build(out_dir, lang, args.tm, args.template, available=available)
        out_path = out_dir / ".ai" / _report_filename(lang)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        _code, _name, _dir = _lang_meta(lang)
        _shipped = " (on-demand: chrome→English)" if _code not in LANGS else ""
        print(f"wrote {out_path}  (lang={_code}, dir={_dir}{_shipped}, switcher={len(available) if len(available) > 1 else 0})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
