#!/usr/bin/env python3
"""freshness_config.py — surgical, schema-aware writer for the DeepInit FRESHNESS keys
in `.ai/deepinit.config` (NO LLM, NO network, stdlib only).

Background: `.ai/deepinit.config` is normally **read-only input** to a run — a DeepInit *run*
never writes it (SKILL.md, triggers.md). This helper is the ONE deliberate, narrow exception:
the user-invoked `/deep-init:customize` → Freshness step may, on the user's explicit confirmation,
persist just the freshness toggles. It is **surgical** — it upserts ONLY the managed freshness keys
and leaves every other key, comment, and the file's layout byte-for-byte intact (so a hand-tuned,
jsonc-commented config survives a freshness edit). Each value is validated against the config schema's
enums/number type before it is written, so a typo can't land an invalid value.

Managed keys (and the schema rule each is checked against):
  notify-on-session-start / check-on-session-start / notify-on-commit / auto-update  → enum on|off
  notify-cadence                                                                     → enum session|window|always
  notify-window-hours                                                                → number >= 0

CLI:
  python freshness_config.py --root <repo> --set notify-cadence=window --set notify-window-hours=12 [--apply]
  (default = PREVIEW to stdout / no write; --apply writes <root>/.ai/deepinit.config). Exit 2 on a bad value.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ── the managed freshness keys + their schema rule (kept in lockstep with deepinit.config.schema.json) ──
_ENUM = {
    "notify-on-session-start": {"on", "off"},
    "check-on-session-start": {"on", "off"},   # back-compat alias of notify-on-session-start
    "notify-on-commit": {"on", "off"},
    "auto-update": {"on", "off"},
    "notify-cadence": {"session", "window", "always"},
}
_NUMERIC = {"notify-window-hours"}
MANAGED = set(_ENUM) | _NUMERIC
SCHEMA_POINTER = "./deepinit.config.schema.json"


def validate(key: str, raw: str):
    """Return (ok, value_or_errormsg). Value is the typed Python value to serialize."""
    if key not in MANAGED:
        return False, f"unknown freshness key '{key}' (managed: {', '.join(sorted(MANAGED))})"
    if key in _NUMERIC:
        try:
            n = float(raw)
        except (TypeError, ValueError):
            return False, f"{key} must be a number >= 0 (got '{raw}')"
        if n < 0:
            return False, f"{key} must be >= 0 (got {raw})"
        return True, (int(n) if n == int(n) else n)
    if raw not in _ENUM[key]:
        return False, f"{key} must be one of {sorted(_ENUM[key])} (got '{raw}')"
    return True, raw


def _fmt(key: str, value) -> str:
    """Serialize a validated value as the JSON literal to embed (number bare, enum quoted)."""
    return str(value) if key in _NUMERIC else f'"{value}"'


def _insert_top_level(text: str, key: str, literal: str) -> str:
    """Insert `"key": literal` at the FRONT of the top-level object (right after the opening '{').

    Front-insertion is the safe placement: it never has to retrofit a trailing comma onto an existing
    entry (the brittle part of JSON text-editing) — our new entry gets the comma and the prior content
    follows unchanged. Comments after '{' stay attached to whatever followed them."""
    i = text.find("{")
    if i < 0:                                  # no object at all → create a minimal one
        return '{\n  "%s": %s\n}\n' % (key, literal)
    j = text.rfind("}")
    if j < i:
        return '{\n  "%s": %s\n}\n' % (key, literal)
    inner = text[i + 1:j]
    if inner.strip() == "":                    # empty object {}
        new_inner = '\n  "%s": %s\n' % (key, literal)
    else:
        new_inner = '\n  "%s": %s,%s' % (key, literal, inner)
    return text[:i + 1] + new_inner + text[j:]


def set_freshness(text: str, updates: dict) -> tuple[str, list[str]]:
    """Surgically upsert the freshness `updates` into config `text`. Touch ONLY those keys.

    - If a key already exists at top level (a simple string/number value), replace its value IN PLACE,
      preserving position, key, and surrounding layout/comments.
    - Else insert it at the front of the object.
    - Ensure a "$schema" pointer is present so the editor validates the file.
    Returns (new_text, warnings). Deterministic: same (text, updates) -> same output."""
    warnings: list[str] = []
    if text.strip() == "":
        text = "{}\n"
    # upsert in a FIXED key order so the result is stable regardless of dict iteration order
    for key in sorted(updates):
        literal = _fmt(key, updates[key])
        pat = re.compile(
            r'("' + re.escape(key) + r'"\s*:\s*)("(?:[^"\\]|\\.)*"|-?[0-9][0-9.]*|true|false|null)'
        )
        m = pat.search(text)
        if m:
            text = text[:m.start(2)] + literal + text[m.end(2):]
        else:
            text = _insert_top_level(text, key, literal)
    if '"$schema"' not in text:
        text = _insert_top_level(text, "$schema", f'"{SCHEMA_POINTER}"')
    return text, warnings


def _parse_sets(pairs: list[str]) -> tuple[dict, list[str]]:
    updates, errors = {}, []
    for p in pairs or []:
        if "=" not in p:
            errors.append(f"--set expects KEY=VALUE (got '{p}')")
            continue
        key, raw = p.split("=", 1)
        key, raw = key.strip(), raw.strip()
        ok, val = validate(key, raw)
        if not ok:
            errors.append(val)
        else:
            updates[key] = val
    return updates, errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Surgical, schema-aware writer for DeepInit freshness config keys.")
    ap.add_argument("--root", default=".", help="repo root (writes <root>/.ai/deepinit.config)")
    ap.add_argument("--set", action="append", dest="sets", metavar="KEY=VALUE",
                    help="a freshness key to set (repeatable)")
    ap.add_argument("--apply", action="store_true", help="write the file (default: preview to stdout, no write)")
    a = ap.parse_args(argv)

    updates, errors = _parse_sets(a.sets)
    if errors:
        for e in errors:
            print(f"freshness_config: {e}", file=sys.stderr)
        return 2
    if not updates:
        print("freshness_config: nothing to set (use --set KEY=VALUE)", file=sys.stderr)
        return 2

    cfg = Path(a.root) / ".ai" / "deepinit.config"
    text = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    new_text, warnings = set_freshness(text, updates)
    for w in warnings:
        print(f"freshness_config: {w}", file=sys.stderr)

    if a.apply:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(new_text, encoding="utf-8")
        print(f"freshness_config: wrote {cfg} ({', '.join(f'{k}={updates[k]}' for k in sorted(updates))})")
    else:
        sys.stdout.write(new_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
