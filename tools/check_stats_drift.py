#!/usr/bin/env python3
"""check_stats_drift.py — count-drift guard (Phase-6 Track A, P6-A2).

Asserts that the UNAMBIGUOUS current-state figures cited in the human-facing docs
(README, product page) equal the authoritative values in validation/STATS.json — so a
hand-typed headline number cannot silently rot (the readiness-audit finding).

DELIBERATELY NARROW: it checks a small, declared whitelist of CURRENT-state claims, NOT
free prose. Historical narration ("harness 132 → 140 → 150", "v0.8.0 added …") is advisory
and intentionally NOT policed — only the figures a reader takes as "the number today".

Run standalone (CI): `python tools/check_stats_drift.py` — exit 1 on any drift.
First runs `build_stats.py --check` so STATS.json itself is current before comparing docs to it.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:                                              # be locale-independent (Windows cp1255 can't encode arrows)
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
VAL = ROOT / "validation"


def load_stats() -> dict:
    p = VAL / "STATS.json"
    if not p.exists():
        print("STATS.json missing — run `python tools/build_stats.py`", file=sys.stderr)
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


# Files where a harness-count literal is plausibly a CURRENT-state claim (not a Run log). CLAUDE.md is handled
# separately (claude_md_current_harness_counts — LESSON 2) since DeepInit regenerates it; this advisory scan is
# for the HUMAN-authored docs whose prose is not regenerated.
_PROSE_FILES = ["README.md", "docs/deepinit-product-page.html"]
# A harness keyword must sit near the N/N for it to be a candidate harness-count literal.
_HARNESS_KW = re.compile(r"harness|all-PASS|deterministic check|regression oracle|_chat_validation|must not regress|must stay", re.I)
# Markers that make an N/N HISTORICAL (a past snapshot) → never flag.
_HIST_KW = re.compile(r"at the time|untouched|stays|prior|throughout|→|->|was |grew|Run \d|earlier|then\b|v0\.\d", re.I)


def scan_prose_harness_counts(total: int) -> list[str]:
    """ADVISORY (non-failing): surface candidate STALE current-state harness-count literals
    (an `N/N` adjacent to a harness keyword, with N != total, that does not read as historical).
    Catches drift for human review without false-failing on the dense historical narration."""
    warnings: list[str] = []
    for rel in _PROSE_FILES:
        fp = ROOT / rel
        if not fp.exists():
            continue
        text = fp.read_text(encoding="utf-8")
        for m in re.finditer(r"(\d{2,4})/(\d{2,4})", text):
            n1, n2 = m.group(1), m.group(2)
            if n1 != n2:                                   # only self-equal "N/N PASS"-style claims
                continue
            if int(n1) == total:                           # already current
                continue
            lo, hi = max(0, m.start() - 55), min(len(text), m.end() + 55)
            window = text[lo:hi]
            if not _HARNESS_KW.search(window):             # not a harness claim (e.g. "69/69 citations")
                continue
            if _HIST_KW.search(window):                    # an explicit historical snapshot → leave it
                continue
            line_no = text.count("\n", 0, m.start()) + 1
            warnings.append(f"[{rel}:{line_no}] candidate stale harness-count '{n1}/{n2}' (current total={total}) — ...{window.strip()[:70]}...")
    return warnings


def claude_md_current_harness_counts(total: int) -> tuple[list[str], int]:
    """LESSON 2 — phrasing-AGNOSTIC current-state harness-count gate for the now-GENERATED CLAUDE.md.

    DeepInit OWNS/regenerates CLAUDE.md, so pinning its exact prose ("the count is now N/N", "must not regress")
    is brittle — the wording shifts every regen (the dogfood broke the old hard-coded checks until the generated
    wording was matched). Instead: find every current-state harness-count literal (an `N/N` adjacent to a harness
    keyword, not reading as historical) and HARD-FAIL any that != the STATS total. Reads the count from STATS (the
    stable anchor), never from a hard-coded phrase. Returns (failures, n_checked)."""
    fp = ROOT / "CLAUDE.md"
    if not fp.exists():
        return ([], 0)
    text = fp.read_text(encoding="utf-8")
    failures, checked = [], 0
    for m in re.finditer(r"(\d{2,4})/(\d{2,4})", text):
        n1, n2 = m.group(1), m.group(2)
        if n1 != n2:                                       # only self-equal "N/N PASS"-style claims
            continue
        lo, hi = max(0, m.start() - 55), min(len(text), m.end() + 55)
        window = text[lo:hi]
        if not _HARNESS_KW.search(window):                 # not a harness claim (e.g. "9/9 recall")
            continue
        if _HIST_KW.search(window):                        # an explicit historical snapshot → not current-state
            continue
        checked += 1
        line_no = text.count("\n", 0, m.start()) + 1
        if int(n1) != total:
            failures.append(f"[CLAUDE.md:{line_no}] current-state harness count '{n1}/{n2}' != STATS total {total} "
                            f"— ...{window.strip()[:60]}...")
    return failures, checked


def timing_figure_checks(timing: dict) -> list:
    """The four metered MARKETING figures — parallel speedup · throughput (LOC/sec) · cost+time per S/M/L
    tier · repo-size scaling — drift-guarded against STATS.timing (the §36 spine extended to the product page).

    DORMANT-UNTIL-MEASURED: returns [] unless STATS.timing.publishable_figure_ready is true (which, per §83 G3,
    requires time_source_floor == external_metered AND all S/M/L tiers measured — i.e. a real metered M7 corpus).
    Until then NO marketing figure is published (honest no-data), so there is nothing to guard. The MACHINERY is
    wired now so the guard auto-activates the moment the metered runs flip the flag — a hand-typed speedup/
    throughput/cost number can never then silently rot. (The exact page wording + STATS keys are finalized when
    the figures land; these regexes pin the contract.)"""
    if not timing.get("publishable_figure_ready"):
        return []
    by_tier = timing.get("by_tier", {}) or {}
    thr = timing.get("throughput", {}) or {}
    par = timing.get("parallelism", {}) or {}
    page = "docs/deepinit-product-page.html"
    L = by_tier.get("L", {}) or {}
    return [
        (page, "parallel speedup", r"~?<strong>([\d.]+)×</strong>\s*(?:parallel\s*)?speedup", {str(par.get("wave_2a_speedup_median"))}),
        (page, "throughput LOC/sec", r"<strong>([\d.]+)\s*LOC/sec</strong>", {str(thr.get("loc_per_sec_median"))}),
        (page, "cost+time L-tier wall", r"L[- ]tier[^<]*<strong>([\d.]+)\s*s</strong>", {str(L.get("wall_time_sec_median"))}),
        (page, "repo-size scaling LOC", r"~flat[^.]*?(\d+)k[- ]line", {str(thr.get("size_scaling_loc_k"))}),
    ]


def package_stats_copy_in_sync() -> list[str]:
    """ISS-006 — the product-page package ships a COPY of validation/STATS.json at
    docs/product-page-package/source-evidence/STATS.json (the package README prescribes a manual re-copy).
    That copy was UN-GATED and silently drifted (its harness total read 246 while the authoritative was 349+).
    Pin it: the copy MUST be byte-identical to the authoritative validation/STATS.json (both are byte-stable
    build_stats.py output). build_stats.py now auto-refreshes this copy on every regen, so a drift here means
    the regen was skipped — re-run `python tools/build_stats.py` (which refreshes it), or cp manually:
        cp validation/STATS.json docs/product-page-package/source-evidence/STATS.json
    """
    auth = VAL / "STATS.json"
    shadow = ROOT / "docs" / "product-page-package" / "source-evidence" / "STATS.json"
    if not shadow.exists():
        return []  # the product-page package is website-only (not shipped in this repo) — nothing to keep in sync
    if auth.read_bytes() == shadow.read_bytes():
        return []
    # Not byte-identical — surface the figure-level deltas for a fast diagnosis (not just "bytes differ").
    try:
        ha = json.loads(auth.read_text(encoding="utf-8")).get("harness", {})
        hb = json.loads(shadow.read_text(encoding="utf-8")).get("harness", {})
        deltas = [f"{k}: copy={hb.get(k)} vs authoritative={ha.get(k)}"
                  for k in ("total", "sections", "mutation_count") if ha.get(k) != hb.get(k)]
        hint = "; ".join(deltas) or "content differs"
    except Exception:
        hint = "content differs (copy is not valid JSON?)"
    return [f"[docs/product-page-package/source-evidence/STATS.json] STALE copy of validation/STATS.json ({hint}). "
            f"Re-run `python tools/build_stats.py` (refreshes it), or cp validation/STATS.json docs/product-page-package/source-evidence/STATS.json"]


def main() -> int:
    # 0) STATS.json must itself be current vs the records (no point checking docs against a stale aggregate).
    rc = subprocess.run([sys.executable, str(ROOT / "tools" / "build_stats.py"), "--check"]).returncode
    if rc != 0:
        print("DRIFT: STATS.json is stale vs the records. Run `python tools/build_stats.py`, then re-check.", file=sys.stderr)
        return 1

    s = load_stats()
    harness = s["harness"]
    oracle = harness.get("oracle", {})
    mirror = s.get("mirror", {}).get("held_out") or {}
    precision = s.get("precision", {})
    stacks = s.get("stacks", {})

    total = harness.get("total")
    sections = harness.get("sections")
    mutation_count = harness.get("mutation_count")
    held_repos = len(mirror.get("repos") or [])
    recall_n, recall_d = oracle.get("recall_n"), oracle.get("recall_d")
    mfp = oracle.get("metamorphic_fp")
    cov_pct_round = round((mirror.get("coverage", {}).get("pct") or 0) * 100)          # 81
    cov_pct_1dp = round((mirror.get("coverage", {}).get("pct") or 0) * 100, 1)         # 80.7
    faith_pct = round((mirror.get("faithfulness", {}).get("pct") or 0) * 100)          # 96
    naive = precision.get("naive_fp_avoided_total")
    nstacks = stacks.get("count")
    matrix = s.get("matrix", {})
    mx_repos = matrix.get("repo_count")
    mx_langs = matrix.get("language_count")
    mx_parse = matrix.get("graphify_parseable_count")

    # Each check: (file, label, regex with ONE capture group, expected str). The regex pins the CURRENT-state
    # context so a historical mention does not match. Multiple acceptable renderings → a tuple of expecteds.
    CHECKS = [
        ("README.md", "harness check count", r"\*\*(\d+) deterministic checks\*\*", {str(total)}),
        ("README.md", "oracle recall n/d", r"recall \*\*(\d+/\d+) \(\d+%, Wilson95", {f"{recall_n}/{recall_d}"}),
        ("README.md", "metamorphic-FP", r"\*\*(\d+/\d+) metamorphic false-positives\.?\*\*", {f"{mfp}/{recall_d}"}),
        ("README.md", "matrix repos", r"\*\*(\d+)-repo / \d+-language / \d-size matrix\*\*", {str(mx_repos)}),
        ("README.md", "matrix languages", r"\*\*\d+-repo / (\d+)-language / \d-size matrix\*\*", {str(mx_langs)}),
        ("README.md", "matrix parseable", r"(\d+) of \d+ parse on the designed AST path", {str(mx_parse)}),
        ("docs/deepinit-product-page.html", "harness check count", r"A (\d+)-check regression harness", {str(total)}),
        ("docs/deepinit-product-page.html", "Mirror coverage %", r"~<strong>(\d+)%</strong> of what the human docs state", {str(cov_pct_round), str(cov_pct_1dp)}),
        ("docs/deepinit-product-page.html", "Mirror faithfulness %", r"<strong>(\d+)% faithfulness</strong>", {str(faith_pct)}),
        ("docs/deepinit-product-page.html", "metamorphic-FP card", r"(\d+/\d+) on real bugfixes", {f"{mfp}/{recall_d}"}),
        # M7 page-overhaul figures (self-derive from STATS, drift-guarded)
        ("docs/deepinit-product-page.html", "oracle sections", r"(\d+) oracle sections", {str(sections)}),
        ("docs/deepinit-product-page.html", "mutation count", r"(\d+) of \d+ mutations killed", {str(mutation_count)}),
        ("docs/deepinit-product-page.html", "held-out repo count", r"(\d+) held-out repos", {str(held_repos)}),
        # NOTE (LESSON 2 — 2026-06-15 dogfood): CLAUDE.md is DELIBERATELY NOT pinned here by an exact prose
        # phrasing. DeepInit now OWNS/regenerates CLAUDE.md (the "owns the front door" model), so hard-coding its
        # wording ("the count is now N/N", "re-run the harness — N/N must not regress") is brittle — a regen
        # shifts the prose and false-breaks the guard (exactly what the dogfood hit). Its current-state harness
        # count is instead checked phrasing-AGNOSTICALLY below (claude_md_current_harness_counts), reading the
        # count from STATS.json (the stable anchor), not from front-door prose.
    ]

    # Per-fact-kind held-out coverage — the honest strengths-and-frontier breakdown on the product page
    # (A4 / v0.34). Each published "<kind> <strong>NN%</strong>" MUST equal round(coverage_by_kind.<kind>.pct*100),
    # so a re-score can't leave a stale per-kind figure on the page (the recompute-honesty rule, extended to the
    # marketing breakdown). New STATS-derived figure ⇒ a matching CHECK, per the page's own ethos.
    cbk = mirror.get("coverage_by_kind", {})
    for _kind in ("component-exists", "component-role", "entry-point", "dependency-edge",
                  "technology-choice", "data-store", "boundary-rule", "key-invariant"):
        _pct = cbk.get(_kind, {}).get("pct")
        if _pct is not None:
            CHECKS.append(("docs/deepinit-product-page.html", f"coverage {_kind}",
                           rf"{re.escape(_kind)} <strong>(\d+)%</strong>", {str(round(_pct * 100))}))

    # The four metered marketing figures — wired + gated, dormant until a metered M7 corpus flips
    # STATS.timing.publishable_figure_ready (then the guard activates automatically; no figure published until then).
    _timing_checks = timing_figure_checks(s.get("timing", {}))
    CHECKS = CHECKS + _timing_checks
    if not _timing_checks:
        print("  [DORMANT] 4 metered marketing figures (parallel speedup · throughput · cost+time/tier · repo-size scaling)"
              " — inactive until STATS.timing.publishable_figure_ready flips (a metered M7 real-engine corpus; honest no-data)")

    failures = []
    checked = 0
    for rel, label, rx, expected in CHECKS:
        if any("None" in str(e) for e in expected):
            continue  # figure not derivable in this build (e.g. the held-out-key oracle is absent in a public release) — published in the doc, not drift-gated
        fp = ROOT / rel
        if not fp.exists():
            continue  # file not shipped in this repo (e.g. the product page lives on the website) — skip its checks
        text = fp.read_text(encoding="utf-8")
        m = re.search(rx, text)
        if not m:
            failures.append(f"[{rel}] {label}: pattern not found (/{rx}/) — page wording changed? update the guard")
            continue
        checked += 1
        got = m.group(1)
        if got not in expected:
            failures.append(f"[{rel}] {label}: doc says '{got}', STATS.json says {sorted(expected)}")
        else:
            print(f"  [OK] {rel}: {label} = {got}")

    # LESSON 2 — CLAUDE.md current-state harness count, checked phrasing-agnostically (DeepInit regenerates it).
    cm_failures, cm_checked = claude_md_current_harness_counts(total)
    failures.extend(cm_failures)
    checked += cm_checked

    # ISS-006 — the product-page package's STATS.json copy must stay byte-identical to the authoritative file.
    pkg_failures = package_stats_copy_in_sync()
    if pkg_failures:
        failures.extend(pkg_failures)
    else:
        print("  [OK] docs/product-page-package/source-evidence/STATS.json: byte-identical to validation/STATS.json")
    checked += 1

    # Advisory in-prose scan (M7-8e) — never fails the build; surfaces candidate stale literals.
    advisory = scan_prose_harness_counts(total)
    if advisory:
        print()
        print(f"ADVISORY — {len(advisory)} candidate stale harness-count literal(s) (verify current-state vs historical):")
        for w in advisory:
            print("  [WARN] " + w)

    print()
    if failures:
        print("COUNT-DRIFT DETECTED:")
        for f in failures:
            print("  [DRIFT] " + f)
        print(f"\n{len(failures)} drift(s). Update the doc to STATS.json, or fix the guard if wording moved.")
        return 1
    print(f"No drift — {checked} current-state figures match STATS.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
