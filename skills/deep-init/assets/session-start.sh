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
#   window (DEFAULT)  = at most once per notify-window-hours (default 24h) of wall-clock back-off, so a dev
#                       opening many short sessions in a day isn't re-nudged in each one;
#   session           = once per NEW session — dedup on the SessionStart session_id (stdin JSON);
#   always            = every session start while stale.
# REMEMBER-DECLINES: when the user answers the offer with "Not now", the agent records a back-off via
#   `deepinit_status.py --snooze` (writes .ai/.deepinit-nudge-snooze = now + notify-snooze-hours, default 168h
#   / one week); this hook honors that snooze below, so "Not now" means "not for a while", not just this prompt.
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

# --- SNOOZE gate (remember declines): a prior "Not now" recorded a wall-clock back-off — stay silent until it
#     expires. Cheap (cat + date), runs before the cadence gate + the tree hash. The expiry is written by the
#     agent via `deepinit_status.py --snooze` when the user declines the offer (the hook can't observe the
#     AskUserQuestion answer itself), so a decline silences ALL events/cadences until the snooze lapses.
SNOOZE="$ROOT/.ai/.deepinit-nudge-snooze"
if [ -f "$SNOOZE" ]; then
  _snz_now="$(date +%s 2>/dev/null || echo 0)"
  _snz_exp="$(cat "$SNOOZE" 2>/dev/null)"; case "$_snz_exp" in ''|*[!0-9]*) _snz_exp=0;; esac
  [ "$_snz_now" -ne 0 ] && [ "$_snz_now" -lt "$_snz_exp" ] && exit 0
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
CADENCE="$(cfg notify-cadence window)"
STATE="$ROOT/.ai/.deepinit-nudge-state"
SID="$(json_str "$INPUT" session_id)"
EVENT="$(json_str "$INPUT" hook_event_name)"; [ -n "$EVENT" ] || EVENT="SessionStart"

_within_window() {  # true (0) iff a stored unix timestamp is still inside notify-window-hours of now (no write)
  local now win last
  now="$(date +%s 2>/dev/null || echo 0)"
  win="$(awk "BEGIN{w=($(cfg_num notify-window-hours 24))*3600; if(w<=0)w=86400; printf \"%d\", w}" 2>/dev/null || echo 86400)"
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
      _within_window && exit 0                   # no session id (older Claude Code / no stdin) → 24h fallback
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
"$PY" - "$STATUSLINE" "$EVENT" "$CHANGES" "$STATUS" "$ROOT" "$PY" <<'PYEOF' 2>/dev/null
import json, sys
line = sys.argv[1] if len(sys.argv) > 1 else "DeepInit docs look stale."
event = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else "SessionStart"
changes = sys.argv[3] if len(sys.argv) > 3 else ""
status = sys.argv[4] if len(sys.argv) > 4 else ""
root = sys.argv[5] if len(sys.argv) > 5 else "."
interp = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else "python3"   # the hook-resolved interpreter (python3||python), so the snooze cmd runs on a python3-only host
detail = (" Files changed: " + changes + ".") if changes else ""
snooze = ('"' + interp + '" "' + status + '" --root "' + root + '" --snooze') if status else "/deep-init:customize -> Freshness"
ctx = (
    "DeepInit freshness check: the generated context layer (CLAUDE.md + .ai/docs) is STALE relative to "
    "the current code. " + line + detail + " Your FIRST action in this turn, BEFORE you address the "
    "user's request, MUST be to call AskUserQuestion to offer a one-click refresh with three options: "
    "'Update now' (then run /deep-init:refresh), 'Not now' (do nothing), and \"Don't ask in this repo\" "
    "(then create the file .claude/.deepinit-no-nudge to silence future prompts here). If the user chooses "
    "'Not now', record the decline so DeepInit backs off and won't re-ask for about a week — run: " + snooze + " "
    "(a 0-token write; do NOT run any other command for this). After the user answers, carry on with their "
    "original request. Do NOT run the update automatically - the user decides. Persistent freshness settings "
    "(turn the nudge off, change the cadence/time-window) live in /deep-init:customize -> Freshness. This was "
    "a 0-token deterministic check, not the update itself."
)
print(json.dumps({
    "hookSpecificOutput": {"hookEventName": event, "additionalContext": ctx},
    "systemMessage": line + detail + "  -  I'll offer a one-click refresh; /deep-init:customize -> Freshness to change or turn this off.",
}))
PYEOF
exit 0
