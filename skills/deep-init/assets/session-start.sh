#!/bin/bash
# DeepInit freshness hook — proactive, 0-token (no LLM, no network) docs-staleness SUGGESTION.
#
# Shipped as a PLUGIN hook (hooks/hooks.json), so it's active wherever the deep-init plugin is enabled
# — no per-repo install. It backs BOTH events that hooks/hooks.json wires to it: SessionStart (a session
# opens) AND UserPromptSubmit (the user submits a prompt — re-surfaces the offer at the first prompt and
# catches staleness that appears mid-session, e.g. just after a commit). On either, it checks whether the
# generated context layer (CLAUDE.md + .ai/docs) has fallen behind the code; if so it injects an imperative
# instruction asking the agent to OFFER a one-click refresh FIRST (a hook can only inject text, not draw a
# button — and VS Code drops a hook's systemMessage — so the reliable surface is the agent calling
# AskUserQuestion). It NEVER runs the costly update itself, self-gates when fresh / disabled / already-
# nudged-this-session (one shared cadence gate across both events), and is trivial to silence.
#
# CADENCE (notify-cadence in .ai/deepinit.config):
#   session (DEFAULT) = once per NEW session — dedup on the SessionStart session_id (stdin JSON), so an
#                       actively-committing dev gets nudged each genuinely-new session, never twice in one;
#   window            = at most once per notify-window-hours (wall-clock back-off, the old behavior);
#   always            = every session start while stale.
# Disable: .claude/.deepinit-no-nudge, notify-on-session-start:"off", `claude plugin disable deep-init`,
# or disableAllHooks. Tune it all the safe way via /deep-init:customize → Freshness. See references/triggers.md.
set -u
export PYTHONUTF8=1   # consistent UTF-8 from the status script regardless of the shell's locale

# --- read the hook's stdin JSON once (carries session_id / source). Never block: only read when stdin is
#     a pipe (the hook path); a manual terminal run (tty) skips it so the script can't hang waiting on EOF.
INPUT=""
[ ! -t 0 ] && INPUT="$(cat 2>/dev/null || true)"

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo .)"
CONFIG="$ROOT/.ai/deepinit.config"

# --- DISABLE switches (any one silences it). Global off = Claude Code's own disableAllHooks /
#     `claude plugin disable deep-init` (handled upstream, no code needed here).
[ -f "$ROOT/.claude/.deepinit-no-nudge" ] && exit 0          # per-repo "Don't ask in this repo" flag
if [ -f "$CONFIG" ] && grep -Eq '"(notify-on-session-start|check-on-session-start)"[[:space:]]*:[[:space:]]*"off"' "$CONFIG" 2>/dev/null; then
  exit 0
fi

# tiny flat-JSON readers for .ai/deepinit.config (return DEFAULT when the key is absent/unset).
# cfg() mirrors post-commit.sh byte-for-byte — one source of truth for the string-value config-read shape.
cfg() {  # cfg KEY DEFAULT  → a "string" value
  local v=""
  [ -f "$CONFIG" ] && v="$(grep -o "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$CONFIG" 2>/dev/null | head -1 | grep -o '"[^"]*"$' | tr -d '"')"
  printf '%s' "${v:-$2}"
}
cfg_num() {  # cfg_num KEY DEFAULT  → an unquoted JSON number
  local v=""
  [ -f "$CONFIG" ] && v="$(grep -o "\"$1\"[[:space:]]*:[[:space:]]*[0-9][0-9.]*" "$CONFIG" 2>/dev/null | head -1 | grep -o '[0-9][0-9.]*$')"
  printf '%s' "${v:-$2}"
}
json_str() {  # json_str BLOB KEY  → a "string" field from a JSON blob (same shape as cfg)
  printf '%s' "$1" | grep -o "\"$2\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" 2>/dev/null | head -1 | grep -o '"[^"]*"$' | tr -d '"'
}

# --- locate python + the deterministic status keystone (a sibling plugin asset; fall back to a copy)
PY="$(command -v python3 || command -v python || true)"
STATUS=""
for c in "$HERE/deepinit_status.py" "${CLAUDE_PLUGIN_ROOT:-}/skills/deep-init/assets/deepinit_status.py" "$ROOT/.ai/deepinit_status.py"; do
  [ -n "$c" ] && [ -f "$c" ] && STATUS="$c" && break
done
[ -n "$PY" ] && [ -n "$STATUS" ] || exit 0

# --- CADENCE pre-gate (cheap): how often the nudge re-fires while the docs stay stale (default = once per
#     new session). Run this BEFORE the tree-hashing keystone so an already-nudged session/window short-
#     circuits without re-hashing the tracked files on every UserPromptSubmit. The state file
#     (.ai/.deepinit-nudge-state) records the last-nudged session id (session cadence) OR a unix timestamp
#     (window/fallback), and is written ONLY when we actually emit (below) — never here — so a fresh session
#     can't suppress a later stale one inside its window.
CADENCE="$(cfg notify-cadence session)"
STATE="$ROOT/.ai/.deepinit-nudge-state"
SID="$(json_str "$INPUT" session_id)"
EVENT="$(json_str "$INPUT" hook_event_name)"; [ -n "$EVENT" ] || EVENT="SessionStart"

_within_window() {  # true (0) iff a stored unix timestamp is still inside notify-window-hours of now (no write)
  local now win last
  now="$(date +%s 2>/dev/null || echo 0)"
  win="$(awk "BEGIN{w=($(cfg_num notify-window-hours 6))*3600; if(w<=0)w=21600; printf \"%d\", w}" 2>/dev/null || echo 21600)"
  [ -f "$STATE" ] && [ "$now" -ne 0 ] || return 1
  last="$(cat "$STATE" 2>/dev/null)"; case "$last" in ''|*[!0-9]*) last=0;; esac
  [ $((now - last)) -lt "$win" ]
}

case "$CADENCE" in
  always) : ;;                                   # no dedup — nudge on every session start / prompt while stale
  window) _within_window && exit 0 ;;            # inside the wall-clock back-off window → silent (skip keystone)
  *)                                             # session (DEFAULT) — once per NEW session id
    if [ -n "$SID" ]; then
      last=""; [ -f "$STATE" ] && last="$(cat "$STATE" 2>/dev/null)"
      [ "$last" = "$SID" ] && exit 0             # same session already nudged (resume/compact/clear/next prompt) → silent
    else
      _within_window && exit 0                   # no session id (older Claude Code / no stdin) → 6h fallback
    fi
    ;;
esac

# --- compute staleness (0 tokens). Only now, past the cheap pre-gate, do we hash the tracked files.
#     --summary => line 1 is the canonical STALE/fresh line (the cross-file grep contract); line 2, when
#     stale, lists WHAT changed (paths + owning components) so the offer shows detail, not just a count.
OUT="$("$PY" "$STATUS" --root "$ROOT" --summary 2>/dev/null)"
STATUSLINE="$(printf '%s\n' "$OUT" | sed -n '1p')"
CHANGES="$(printf '%s\n' "$OUT" | sed -n '2p')"
case "$STATUSLINE" in *"docs STALE"*) ;; *) exit 0 ;; esac   # fresh / no state → silent, and NO state write

# --- record that we nudged (so the next prompt / session dedups). Written ONLY on a real emit.
case "$CADENCE" in
  always) : ;;                                   # never record — fire every time while stale
  window) _now="$(date +%s 2>/dev/null || echo 0)"; [ "$_now" -ne 0 ] && echo "$_now" > "$STATE" 2>/dev/null ;;
  *) if [ -n "$SID" ]; then echo "$SID" > "$STATE" 2>/dev/null
     else _now="$(date +%s 2>/dev/null || echo 0)"; [ "$_now" -ne 0 ] && echo "$_now" > "$STATE" 2>/dev/null; fi ;;
esac

# --- emit the freshness payload: a self-contained, actionable systemMessage (CLI surface only — VS Code drops
#     hook systemMessage, so the reliable surface is the agent acting on additionalContext) PLUS the imperative
#     additionalContext telling the agent to OFFER the refresh FIRST. hookEventName mirrors whichever event
#     invoked us (SessionStart or UserPromptSubmit) — Claude Code requires the match to accept the context.
"$PY" - "$STATUSLINE" "$EVENT" "$CHANGES" <<'PYEOF' 2>/dev/null
import json, sys
line = sys.argv[1] if len(sys.argv) > 1 else "DeepInit docs look stale."
event = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else "SessionStart"
changes = sys.argv[3] if len(sys.argv) > 3 else ""
detail = (" Files changed: " + changes + ".") if changes else ""
ctx = (
    "DeepInit freshness check: the generated context layer (CLAUDE.md + .ai/docs) is STALE relative to "
    "the current code. " + line + detail + " Your FIRST action in this turn, BEFORE you address the "
    "user's request, MUST be to call AskUserQuestion to offer a one-click refresh with three options: "
    "'Update now' (then run /deep-init:refresh), 'Not now' (do nothing), and \"Don't ask in this repo\" "
    "(then create the file .claude/.deepinit-no-nudge to silence future prompts here). After the user "
    "answers, carry on with their original request. Do NOT run the update automatically - the user "
    "decides. Persistent freshness settings (turn the nudge off, change the cadence/time-window) live in "
    "/deep-init:customize -> Freshness. This was a 0-token deterministic check, not the update itself."
)
print(json.dumps({
    "hookSpecificOutput": {"hookEventName": event, "additionalContext": ctx},
    "systemMessage": line + detail + "  -  I'll offer a one-click refresh; /deep-init:customize -> Freshness to change or turn this off.",
}))
PYEOF
exit 0
