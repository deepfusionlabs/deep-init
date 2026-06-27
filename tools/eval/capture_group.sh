#!/usr/bin/env bash
# Metered DeepInit-vs-/init capture — GROUPED for parallelism. Usage: capture_group.sh A|B
# Resumable (skips a repo whose deepinit run-1 exists), defensive clone reset, continue-on-error.
set -u
GROUP="${1:?usage: capture_group.sh A|B}"
REPO_ROOT="c:/Src/DeepFusionLabs/deep-init"
WORK="c:/tmp/init-bench"
LOG="$WORK/capture-$GROUP.log"
DATE="2026-06-25"
export DEEPINIT_REAL_ENGINE=1
export PYTHONUTF8=1
mkdir -p "$WORK"

# key|owner/repo|pinned_sha  — balanced so each group carries one heavier repo
if [ "$GROUP" = "A" ]; then
  repos=(
    "itsdangerous|pallets/itsdangerous|672971d66a2ef9f85151e53283113f33d642dabd"
    "gin|gin-gonic/gin|d75fcd4c9ab260e5225de590f1f0f8c0e0e12d11"
    "express|expressjs/express|dae209ae6559c29cfca2a1f4414c51d89ea643d5"
    "uniffi-rs|mozilla/uniffi-rs|c6c518fd49525a2fb69e2b7e2f181d877ee6a570"
  )
elif [ "$GROUP" = "C" ]; then
  # kotlinx-schema's manifest URL 404s; replace with fmt (C++) + commercetools-sync-java (Java/L, obscure)
  repos=(
    "fmt|fmtlib/fmt|11ddbcb7898d2d3445d431a54814367b21dee6ad"
    "commercetools-sync-java|commercetools/commercetools-sync-java|a0fbe1f4e6c83965f1ae96596cb58c084e65e05f"
  )
else
  repos=(
    "gorilla-mux|gorilla/mux|db9d1d0073d27a0a2d9a8c1bc52aa0af4374d265"
    "click|pallets/click|8a1b1a33d739be05b7e91251e3c0dde77c5e152f"
    "sinatra|sinatra/sinatra|5236d3459b8b9015e5ce21ddd0c6beb0db4081d4"
  )
fi

log(){ echo "[$(date +%H:%M:%S)] [$GROUP] $*" | tee -a "$LOG"; }

log "=== group $GROUP start: ${#repos[@]} repos (init K=3 + deepinit K=1) ==="
for entry in "${repos[@]}"; do
  IFS='|' read -r key repo sha <<< "$entry"
  done_marker="$REPO_ROOT/validation/matrix/init-outputs/$key/deepinit/run-1/CLAUDE.md"
  if [ -f "$done_marker" ]; then log "skip $key (already captured)"; continue; fi
  clone="$WORK/$key"
  if [ ! -d "$clone/.git" ]; then
    log "clone $repo …"
    git clone --filter=blob:none --quiet "https://github.com/$repo" "$clone" 2>>"$LOG" || { log "CLONE FAIL $key"; continue; }
  fi
  git -C "$clone" checkout --quiet "$sha" 2>>"$LOG" || { log "CHECKOUT FAIL $key $sha"; continue; }
  git -C "$clone" checkout --quiet -- . 2>/dev/null; git -C "$clone" clean -fdq 2>/dev/null   # defensive reset
  head=$(git -C "$clone" rev-parse HEAD)
  if [ "${head:0:12}" != "${sha:0:12}" ]; then log "SHA MISMATCH $key"; continue; fi
  log "capture $key ($repo @ ${head:0:12}) …"
  python "$REPO_ROOT/tools/run_init_benchmark.py" \
     --repo "$repo" --sha "$sha" --clone "$clone" --key "$key" \
     --arms init,deepinit --init-runs 3 --deepinit-runs 1 \
     --model opus --max-budget-usd 40 --date "$DATE" >>"$LOG" 2>&1 || log "CAPTURE NONZERO $key"
  log "done $key"
done
log "=== group $GROUP COMPLETE ==="
