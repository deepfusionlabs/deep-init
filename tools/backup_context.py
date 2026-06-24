#!/usr/bin/env python3
"""
backup_context.py — the dated, REVERSIBLE backup of a user-authored context file (backlog B2).

DeepInit OWNS the auto-loaded front door: when it runs, its grounded lean tier BECOMES
`CLAUDE.md` (and the cross-tool `AGENTS.md` export / `.cursorrules`). Before it overwrites
any pre-existing user-authored context file, it archives the EXACT pre-run file to a DATED
backup so the change is **reversible** (R9 via reversibility, not in-place freezing). The
backup is:
  - DATED + sortable — `<name>.<YYYY-MM-DDThhmm>.bak` (chronological == lexical order),
  - REDACTED via the R5 secret gate — a previously-untracked secret is NEVER newly
    committed into a backup (defense-in-depth; redaction.md is the full gate, this mirrors
    its built-in no-dependency secret scan),
  - COMMITTED/visible + root-adjacent — visibility = trust; a new/untrusting user can SEE it is
    reversible, so the backup stays NEXT TO the file it backs up (never tucked into .ai/ or a hidden dir),
  - PRUNED to the last N=1 per file — non-accumulating; only the most-recent pre-run state stays in the
    working tree (git history holds the full dated chain, so a PILE of dated .bak's is needless clutter),
  - REVERSIBLE — a no-secret file round-trips BYTE-FOR-BYTE (the backup is the exact
    original); a file carrying a secret has only the secret masked, everything else exact.

Pure + deterministic: the timestamp is an INPUT (no clock), so the harness (§62) can pin it
and the caller stamps the real time. This module computes the PLAN (name, redacted bytes,
prune list); the caller does the actual write/delete + commit (draft-only git discipline).
"""
from __future__ import annotations

import re

DEFAULT_KEEP = 1
REDACTED = "[CREDENTIAL_REDACTED]"

# A focused subset of redaction.md's R5 built-in secret patterns (the no-dependency scan;
# gitleaks/trufflehog, when present, run additionally in the real redaction stage).
_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),                                   # AWS access key id
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),                            # OpenAI-style key
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),                            # GitHub PAT
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),                   # Slack token
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),                # private-key header
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),  # JWT
    # KEY=secret / KEY: secret env-style pairs AND the JSON/YAML quoted-key form ("password": "secret")
    # — the optional closing quote in the separator group (["']?…) catches `"key": "value"`, which the bare
    # `\b(key)\b[=:]` form misses (the `"` between key and colon blocks it). Value masked, key kept.
    re.compile(r"""(?i)\b(password|secret|token|api[_-]?key|access[_-]?key)\b(["']?\s*[=:]\s*)["']?[^\s"']{8,}"""),
]

# Connection strings with embedded credentials (redaction.md:6 lists these explicitly) — mask only the
# PASSWORD between `scheme://user:` and `@host`, keeping the rest (still fails safe: a missed secret is the
# only unsafe outcome, so when in doubt the real redaction.md gate masks more).
_CONN_PATTERN = re.compile(r"(://[^:@/\s]+:)([^@/\s]{3,})(@)")


def dated_backup_name(filename: str, timestamp: str) -> str:
    """`<filename>.<YYYY-MM-DDThhmm>.bak` — `timestamp` is a sortable 'YYYY-MM-DDThhmm'
    string supplied by the caller (no clock here, so the result is deterministic)."""
    return f"{filename}.{timestamp}.bak"


def redact(content: str) -> tuple[str, int]:
    """Mask R5 secrets in `content`; everything else is preserved BYTE-FOR-BYTE.

    Returns (redacted_content, n_masked). n_masked == 0 ⇒ the file round-trips exactly
    (it is fully reversible). When in doubt the real redaction.md gate masks more, never
    less — a false-positive mask is safe, a missed secret is not.
    """
    out = content
    n = 0

    def _kv(m: "re.Match") -> str:
        nonlocal n
        n += 1
        return f"{m.group(1)}{m.group(2)}{REDACTED}"

    def _conn(m: "re.Match") -> str:
        nonlocal n
        n += 1
        return f"{m.group(1)}{REDACTED}{m.group(3)}"   # scheme://user:[REDACTED]@host

    # connection-string embedded password — keep scheme/user/host, mask only the password
    out, _ = _CONN_PATTERN.subn(_conn, out)
    # the KEY=secret pattern keeps the key + separator, masks the value
    out, _ = _SECRET_PATTERNS[-1].subn(_kv, out)
    for pat in _SECRET_PATTERNS[:-1]:
        out, k = pat.subn(REDACTED, out)
        n += k
    return out, n


def prune(existing_backup_names, keep: int = DEFAULT_KEEP) -> list[str]:
    """Given existing dated backup filenames (any order), return the list to DELETE — the
    OLDEST beyond `keep`. Dated `<...>.<YYYY-MM-DDThhmm>.bak` names sort lexically ==
    chronologically, so the last `keep` after a sort are the newest to retain. ≤ keep → []."""
    ordered = sorted(existing_backup_names)            # oldest first
    if len(ordered) <= keep:
        return []
    return ordered[: len(ordered) - keep]


def plan_backup(filename: str, content: str, existing_backup_names, timestamp: str,
                keep: int = DEFAULT_KEEP) -> dict:
    """The full backup PLAN for `filename` (pure — the caller writes/deletes + commits):
      - `backup_name`     the dated `<name>.<ts>.bak`
      - `redacted_content` the R5-redacted bytes to write (== content iff no secret)
      - `secrets_masked`  how many secrets were masked
      - `reversible_exact` True iff the backup is the byte-for-byte original (no secret)
      - `prune_delete`    the OLDEST backups to delete so only the last `keep` survive,
                          counting the new one (non-accumulating).
    """
    name = dated_backup_name(filename, timestamp)
    redacted, n_masked = redact(content)
    to_delete = prune(list(existing_backup_names) + [name], keep=keep)
    return {
        "backup_name": name,
        "redacted_content": redacted,
        "secrets_masked": n_masked,
        "reversible_exact": n_masked == 0,
        "prune_delete": to_delete,
    }


if __name__ == "__main__":
    import json
    import sys
    data = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    print(json.dumps(plan_backup(
        data.get("filename", "CLAUDE.md"), data.get("content", ""),
        data.get("existing", []), data.get("timestamp", "1970-01-01T0000"),
        keep=data.get("keep", DEFAULT_KEEP)), indent=2))
