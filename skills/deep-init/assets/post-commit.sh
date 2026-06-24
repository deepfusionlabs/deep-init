#!/bin/bash
# DeepInit post-commit hook — installed by: /deep-init setup-hooks
#   (1) records the changed files for the next --update (the breadcrumb / advisory accelerator);
#   (2) optional 0-token staleness NUDGE (notify-on-commit, default on);
#   (3) optional detached headless AUTO-UPDATE (auto-update, default OFF — spends tokens, never commits).
# It NEVER blocks or fails the commit (a post-commit hook can't abort one anyway). See triggers.md.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
DEEPINIT_DIR="$ROOT/.ai/docs/current"
[ -d "$DEEPINIT_DIR" ] || exit 0   # repo not deep-init'd → nothing to do

CHANGED="$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null)"

# (1) breadcrumb for the next --update
printf '%s\n' "$CHANGED" >> "$DEEPINIT_DIR/.pending_changes.txt"

# source-commit gate: any changed file that is NOT docs/css/config/lockfile
is_source=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    *.md|*.css|*.txt|*.json|*.lock|*.lockfile|*.yaml|*.yml|*.toml|*.cfg|*.ini) : ;;
    *) is_source=1 ;;
  esac
done <<EOF
$CHANGED
EOF
[ "$is_source" -eq 1 ] || exit 0   # docs/config-only commit → no nudge, no auto-update

# tiny flat-JSON reader for .ai/deepinit.config (returns DEFAULT when the key is absent/unset)
CONFIG="$ROOT/.ai/deepinit.config"
cfg() {  # cfg KEY DEFAULT
  local v=""
  [ -f "$CONFIG" ] && v="$(grep -o "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$CONFIG" 2>/dev/null | head -1 | grep -o '"[^"]*"$' | tr -d '"')"
  printf '%s' "${v:-$2}"
}

PY="$(command -v python3 || command -v python || true)"
STATUS="$ROOT/.ai/deepinit_status.py"   # shipped into the repo by setup-hooks

# (2) NUDGE (default on, 0 tokens) — print the deterministic staleness line.
if [ "$(cfg notify-on-commit on)" != "off" ] && [ -n "$PY" ] && [ -f "$STATUS" ]; then
  "$PY" "$STATUS" --root "$ROOT" --quiet 2>/dev/null || true
fi

# (3) AUTO-UPDATE (default OFF, opt-in, spends tokens) — detached headless run; NEVER auto-commits.
if [ "$(cfg auto-update off)" = "on" ]; then
  LOCK="$DEEPINIT_DIR/.update.lock"
  if command -v claude >/dev/null 2>&1; then
    if ( set -o noclobber; : > "$LOCK" ) 2>/dev/null; then      # lockfile → skip if a run is already in flight
      ( trap 'rm -f "$LOCK"' EXIT                               # detached: `git commit` never waits on the analysis
        claude -p "/deep-init:refresh" >"$DEEPINIT_DIR/.auto-update.log" 2>&1
      ) </dev/null >/dev/null 2>&1 &
      disown 2>/dev/null || true
    fi
  else
    echo "deep-init: auto-update is on, but 'claude' is not on PATH — skipped (run /deep-init:refresh manually)."
  fi
fi
exit 0
