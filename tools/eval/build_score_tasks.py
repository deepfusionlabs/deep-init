#!/usr/bin/env python3
"""Build the blind-scoring work-list from the captured outputs.

Copies each captured CLAUDE.md to an OPAQUE-labelled inbox file (so the scorer can't infer the tool
from the path), and emits tasks.json (for the scoring Workflow) + mapping.json (label -> arm/run,
kept OUT of the scorer's reach for de-anonymisation afterwards)."""
import json, shutil
from pathlib import Path

ROOT = Path("c:/Src/DeepFusionLabs/deep-init")
OUT = ROOT / "validation/matrix/init-outputs"
INBOX = Path("c:/tmp/init-bench/score-inbox")
CLONES = Path("c:/tmp/init-bench")
ORACLES = ROOT / "validation/matrix/oracles"

META = {  # key -> (repo, lang, tier, fame)
    "gin": ("gin-gonic/gin", "Go", "M", "famous"),
    "click": ("pallets/click", "Python", "M", "famous"),
    "express": ("expressjs/express", "JavaScript", "M", "famous"),
    "gorilla-mux": ("gorilla/mux", "Go", "S", "semi"),
    "itsdangerous": ("pallets/itsdangerous", "Python", "S", "obscure"),
    "uniffi-rs": ("mozilla/uniffi-rs", "Rust", "M", "obscure"),
    "kotlinx-schema": ("Kotlin/kotlinx-serialization-json-schema", "Kotlin", "M", "obscure"),
    "sinatra": ("sinatra/sinatra", "Ruby", "M", "famous"),
    "fmt": ("fmtlib/fmt", "C++", "M", "famous"),
    "commercetools-sync-java": ("commercetools/commercetools-sync-java", "Java", "L", "obscure"),
}
ORACLE_KEYS = {"gin", "click", "express"}
POOL = list("ABCDEFGHIJ")

if INBOX.exists():
    shutil.rmtree(INBOX)
INBOX.mkdir(parents=True, exist_ok=True)

tasks, mapping = [], []
for key_dir in sorted(OUT.iterdir()):
    key = key_dir.name
    if key.startswith("_") or key not in META:
        continue
    if not (key_dir / "deepinit" / "run-1" / "CLAUDE.md").exists():
        continue  # skip repos still capturing (no completed deepinit arm yet)
    repo, lang, tier, fame = META[key]
    outs = []
    for arm in ("init", "deepinit"):
        for run_dir in sorted((key_dir / arm).glob("run-*")):
            md = run_dir / "CLAUDE.md"
            if md.exists() and md.stat().st_size > 0:
                outs.append((arm, run_dir.name, md))
    for i, (arm, run, md) in enumerate(outs):
        label = f"{key}-{POOL[i]}"          # opaque to the scorer (no arm in the name)
        anon = INBOX / f"{label}.md"
        shutil.copy2(md, anon)
        tasks.append({
            "key": key, "label": label, "repo": repo, "lang": lang, "tier": tier, "fame": fame,
            "clone": str(CLONES / key).replace("\\", "/"),
            "oracle": str(ORACLES / f"{key}.json").replace("\\", "/") if key in ORACLE_KEYS else None,
            "candidate_path": str(anon).replace("\\", "/"),
        })
        mapping.append({"label": label, "key": key, "arm": arm, "run": run})

(Path("c:/tmp/init-bench/tasks.json")).write_text(json.dumps({"tasks": tasks}, indent=2), encoding="utf-8")
(Path("c:/tmp/init-bench/mapping.json")).write_text(json.dumps(mapping, indent=2), encoding="utf-8")
n_init = sum(1 for m in mapping if m["arm"] == "init")
n_deep = sum(1 for m in mapping if m["arm"] == "deepinit")
print(f"built {len(tasks)} score tasks across {len(set(m['key'] for m in mapping))} repos "
      f"({n_init} /init + {n_deep} deepinit). tasks.json + mapping.json written.")
