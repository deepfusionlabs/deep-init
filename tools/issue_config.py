#!/usr/bin/env python3
"""
issue_config.py — spec §7 issue configuration (BUILT per the Phase-6 implementation
commitment, not "decided-out"). The deterministic reference for three config controls
that wire into C-RAISE (issue-filter.md), each enforced by harness §46:

  1. issues-suppress          — an FP-suppression list of {path-glob, family} entries.
                                A candidate whose file matches a glob AND whose family
                                matches (or family "*") is suppressed-by-config.
  2. issues-language-toggles  — per-language family on/off: {lang: {family: bool}}.
                                A family toggled false for the run's language never fires.
  3. issues-baseline-accept   — per-issue (OQ-3) accept: a list of match-keys that have
                                been individually accepted (complements the bulk
                                .issue_baseline.json). An accepted key is suppressed.

Config lives in `.ai/deepinit.config` (the existing project config; SKILL.md): plain
JSON, long-flag key names without `--`, unknown keys warned-and-ignored (R8 — never
fatal). A config-suppressed candidate is NOT silently dropped: it is reported as a
NAMED suppression with the rule that suppressed it (R8 honesty), exactly like a
predicate-FALSE suppression.
"""
from __future__ import annotations

import re

CONFIG_KEYS = {"issues-suppress", "issues-language-toggles", "issues-baseline-accept"}


def _glob_to_regex(glob: str) -> str:
    """gitignore-style glob → regex. '**' matches across '/', '*' within a segment, '?' one char."""
    i, n, out = 0, len(glob), ["^"]
    while i < n:
        c = glob[i]
        if c == "*":
            if i + 1 < n and glob[i + 1] == "*":
                out.append(".*")          # ** → any chars incl '/'
                i += 2
                if i < n and glob[i] == "/":
                    i += 1                # consume the slash after ** so 'a/**/b' matches 'a/b'
                continue
            out.append("[^/]*")           # * → any chars except '/'
        elif c == "?":
            out.append("[^/]")
        elif c == ".":
            out.append(r"\.")
        else:
            out.append(re.escape(c))
        i += 1
    out.append("$")
    return "".join(out)


def path_matches(glob: str, path: str) -> bool:
    return re.match(_glob_to_regex(glob), path.replace("\\", "/")) is not None


def load_config(text: str) -> tuple[dict, list[str]]:
    """Parse a config JSON string. Returns (config, warnings). Tolerant (R8)."""
    import json
    warnings: list[str] = []
    try:
        cfg = json.loads(text) if text.strip() else {}
    except Exception as e:
        return ({}, [f"config is not valid JSON ({e}); ignored (R8)"])
    if not isinstance(cfg, dict):
        return ({}, ["config is not a JSON object; ignored (R8)"])
    # we only OWN the issue keys here; other deepinit.config keys are handled elsewhere
    return (cfg, warnings)


def should_fire(issue: dict, config: dict, language: str | None = None) -> tuple[bool, str]:
    """Decide whether a candidate issue fires given §7 config. Returns (fire, reason)."""
    fam = issue.get("family", "")
    path = (issue.get("file") or issue.get("path") or "").replace("\\", "/")
    key = issue.get("match_key", "")

    # 1) FP-suppression list (path + rule/family)
    for entry in (config.get("issues-suppress") or []):
        e_fam = entry.get("family", "*")
        e_path = entry.get("path", "**")
        if (e_fam in ("*", fam)) and path and path_matches(e_path, path):
            return (False, f"suppressed by config rule (path '{e_path}', family '{e_fam}')")

    # 2) per-language family toggle
    if language:
        toggles = (config.get("issues-language-toggles") or {}).get(language, {})
        if fam in toggles and toggles[fam] is False:
            return (False, f"family {fam} toggled OFF for language '{language}'")

    # 3) per-issue baseline accept (OQ-3)
    if key and key in (config.get("issues-baseline-accept") or []):
        return (False, f"match-key accepted in baseline ('{key}')")

    return (True, "fires")


if __name__ == "__main__":
    import json
    import sys
    cfg, _ = load_config(sys.stdin.read() if not sys.stdin.isatty() else "{}")
    print(json.dumps(cfg, indent=2))
