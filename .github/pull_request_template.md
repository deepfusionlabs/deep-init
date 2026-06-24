<!-- Thanks for contributing to DeepInit! Please keep this short and check the boxes. -->

## What this changes

<!-- One or two sentences. Link the issue it addresses. -->

Closes #

## Why

<!-- The problem this solves. For a new detector/rule: the defect class + how it stays precise. -->

## Checklist

- [ ] `make validate` (or `python tools/validate_all.py`) is **all-PASS** locally.
- [ ] **Expand-only** — no existing capability removed, the engine not reimplemented.
- [ ] If this adds/changes a detector or rule: a `mini-*` fixture + a harness section + a **killing mutation**
      in `_mutation_harness.py` (proving the new check is load-bearing) are included.
- [ ] No hand-typed figures — any number on the README/docs is derived via `tools/build_stats.py`
      (the drift guard passes).
- [ ] No network dependency, no writing outside the owned region, report-only preserved (100% local).
- [ ] Conventional Commit messages (`feat:` / `fix:` / `docs:` / …).

## Notes for the reviewer

<!-- Anything surprising, a tradeoff you made, or a follow-up you're deferring. -->
