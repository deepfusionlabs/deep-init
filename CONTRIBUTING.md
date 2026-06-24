# Contributing to DeepInit

Thanks for your interest! DeepInit is a **Claude Code skill defined entirely in Markdown** — there is no
application code. The "engine" is a Claude instance executing the instructions in `skills/deep-init/`. Contributing
means improving those instruction files (and the deterministic validation harness that guards them), not
writing a program. Please read this before opening a PR.

## Ground rules (the project's non-negotiables)

DeepInit lives or dies on **trust**, so a few rules are absolute (they mirror `skills/deep-init/references/global-rules.md`):

- **Never fabricate.** Every claim the skill emits must cite a real `file:line` with a certainty tag. A
  confidently-wrong claim is worse than a gap. Changes that loosen grounding will not be accepted.
- **Expand-only.** Extend an existing stage; never remove a capability or reimplement the engine
  (verification, filtering, hashing, generation). Reuse the existing primitives.
- **Report-only, 100% local.** No network calls, no egress, no writing outside the owned region
  (`<!-- DEEPINIT:START -->`…`<!-- DEEPINIT:END -->`) with a `.bak` first.
- **Precision over recall.** A false alarm is what gets a tool turned off. A new detector ships only with a
  measured false-positive story and a fixture that proves its suppressions are load-bearing.

## Local setup

You need Python 3.13 and `pyyaml`. There is nothing to build.

```bash
python -m pip install --upgrade pyyaml
```

## The one "test" — keep it all-PASS

The regression oracle is a deterministic harness over the fixtures (no LLM, no real skill run). It must stay
all-PASS, and the count only grows by addition — the original engine checks must never regress.

```bash
PYTHONUTF8=1 python tests-fixtures-v1/_chat_validation.py     # the harness
PYTHONUTF8=1 python tools/validate_all.py                     # every gate (or: make validate)
```

`make validate` runs the harness + the stats-drift guard + the count-drift guard + the **mutation
meta-harness** (which proves every gated check is load-bearing) + the **public-harness** check.

## How to contribute a change

1. **Open an issue first** for anything non-trivial, so we can agree on the approach.
2. **Design → test → implement, RED before GREEN.** If you add a detector or a rule, add a `mini-*` fixture
   under `tests-fixtures-v1/` with a `ground-truth/expected.json` oracle **and** a harness section that
   asserts it — written so it fails before your change and passes after. Add a killing mutation to
   `_mutation_harness.py` so the new check is provably load-bearing.
3. **Keep one source of truth.** Figures on the README / docs are *derived* from committed records by
   `tools/build_stats.py` — never hand-type a number; run `python tools/build_stats.py` and let the drift
   guard enforce it.
4. **Run `make validate`** and make sure everything is green before you open the PR.
5. **Conventional Commits.** Use `feat:` / `fix:` / `docs:` / `chore:` / `refactor:` / `test:` / `ci:`.

## What we're unlikely to accept

- A detector with no measured false-positive control or no fixture.
- Anything that adds a network dependency, a framework to the dashboard/viewer, or writes outside the owned region.
- A "borrowed" severity or a vendor stat presented as DeepInit's own measurement.
- Scope creep into graph-UI, dedicated security scanning, or cross-model orchestration (out of scope by design).

## Code of Conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Report concerns to
**elad@deepfusionlabs.ai**.

## Security

Please do not open a public issue for a security report — see [SECURITY.md](SECURITY.md).
