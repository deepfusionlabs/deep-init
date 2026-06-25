#!/usr/bin/env python3
"""
i18n_tokens.py — grounded-token protection for DeepInit report translation.

The whole value of DeepInit is that every claim is tied to a `file:line` and an ID.
A translation must therefore NEVER touch the grounded tokens — code, `file:line`
citations, record IDs (BR-/WF-/IP-/ADR-/KL-/ISS-/IF-), and product nouns. This module
is the protect-mask the translate stage uses:

    masked, tokens = mask(english_prose)      # ⟦0⟧ ⟦1⟧ … replace each protected span
    translated_masked = <LLM translates `masked`, preserving the ⟦N⟧ sentinels>
    final = restore(translated_masked, tokens) # put the exact tokens back

and the deterministic VERIFY the builder runs over the stored translation:

    verify(final, tokens)   # True iff every protected token survives verbatim in `final`

`content_key(...)` is the stable cache key for the translation memory (keyed on the
prompt version + lang + glossary hash + source) so re-runs don't re-pay and the output
is byte-stable for a harness gate.

Pure stdlib, no network, no clock, no RNG — the harness pins it deterministically.
Operates on STRUCTURED prose strings, never on rendered HTML.
"""
from __future__ import annotations

import hashlib
import re

# Sentinel: ⟦N⟧ (U+27E6 … U+27E7) — mathematical white square brackets, vanishingly unlikely
# in prose, and the ⟧ terminator means ⟦1⟧ is never a prefix of ⟦10⟧.
_LB, _RB = "⟦", "⟧"


def _sentinel(i: int) -> str:
    return f"{_LB}{i}{_RB}"


# Protected-span patterns, applied in priority order. Earlier patterns mask first; the
# inserted sentinels never match a later pattern, so order resolves overlaps (a citation
# inside a code span is already masked by the time the citation pattern runs). Mirrors the
# grounding tokens build_docs_viewer recognises (cites + the BR/WF/IP/ADR/KL/ISS/IF IDs).
_PATTERNS = [
    re.compile(r"```.*?```", re.S),                              # fenced code block
    re.compile(r"`[^`\n]+`"),                                    # inline code
    re.compile(r"\b[\w./\-]+\.[A-Za-z0-9]+:\d+(?:-\d+)?\b"),     # file:line (needs a dotted ext)
    re.compile(r"\b(?:BR|WF|IP|ADR|KL|ISS|IF)-[A-Za-z0-9:._\-]+"),  # record IDs
    re.compile(r"DeepInit|DeepMap|DeepFusion Labs|CLAUDE\.md|AGENTS\.md|\.ai/"),  # product nouns (verbatim)
]


def mask(text):
    """Return (masked_text, tokens): each protected span replaced by an ⟦N⟧ sentinel,
    `tokens[i]` the verbatim span for sentinel ⟦i⟧."""
    tokens: list[str] = []

    def _repl(m):
        tokens.append(m.group(0))
        return _sentinel(len(tokens) - 1)

    out = text or ""
    for pat in _PATTERNS:
        out = pat.sub(_repl, out)
    return out, tokens


def restore(masked, tokens):
    """Inverse of mask(): put the exact tokens back. restore(*mask(t)) == t."""
    out = masked or ""
    for i, tok in enumerate(tokens or []):
        out = out.replace(_sentinel(i), tok)
    return out


def verify(translated, tokens):
    """True iff every protected token survives VERBATIM in the (restored) translated text —
    the deterministic guard that a translation didn't corrupt a grounded claim. An empty
    token set trivially verifies."""
    t = translated or ""
    return all((tok in t) for tok in (tokens or []))


def content_key(prompt_version, lang, glossary_hash, source):
    """Stable translation-memory cache key. Re-keys (cache-miss → re-translate) whenever the
    prompt version, target language, glossary, or source text changes — so a stale or
    contaminated translation can never silently survive."""
    h = hashlib.sha256()
    h.update("\x1f".join([prompt_version or "", lang or "", glossary_hash or "", source or ""]).encode("utf-8"))
    return h.hexdigest()[:16]
