#!/usr/bin/env python3
"""_mutation_harness.py — mutation testing for the DeepInit validation suite (Phase-6 P6-D1).

The deterministic validation harness (_chat_validation.py) is only trustworthy if its checks are LOAD-BEARING:
a check that stays green when the invariant it guards is violated is VACUOUS (false confidence).
This meta-harness proves they're not — it applies one known-bad mutation at a time to a committed
fixture / skill / aggregate file, runs the FULL harness, and DEMANDS it go RED. A mutation that
SURVIVES (harness still all-PASS) is a vacuous-check finding and fails this meta-harness.

Each mutation is applied IN PLACE then RESTORED (original bytes saved, restored in a finally) so the
working tree is unchanged on exit — even if interrupted.

Guards:
  - BASELINE-GREEN precheck: the unmutated harness MUST pass first (else mutation results are meaningless).
  - HARNESS-STALE guard: if a mutation's find-string is absent (the fixture/skill moved), that mutation
    is reported STALE (not silently skipped) so the meta-harness gets updated alongside the suite.

Run:  PYTHONUTF8=1 python tests-fixtures-v1/_mutation_harness.py
Exit: 0 iff baseline green AND every mutation was KILLED (none survived, none stale).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent            # tests-fixtures-v1
PKG = ROOT.parent                                 # repo root
HARNESS = ROOT / "_chat_validation.py"

# Each mutation: a one-edit corruption of a committed file that MUST make the suite go RED.
# (file, find, replace, label, expects_section)  — distinct categories, each a different gate family.
MUTATIONS = [
    (ROOT / "mini-coverage-record" / "good.json",
     '"deepinit_wrong_high": 0', '"deepinit_wrong_high": 1',
     "§34 hard gate — deepinit_wrong_high must equal the counted wrong+HIGH adjudications (==0)", "§34"),
    (ROOT / "mini-graphify" / "expected-structural-graph.json",
     '"connect()"', '"connectX()"',
     "§35 adapter oracle — the structural-graph adapter output must match the committed oracle", "§35"),
    (PKG / "skills" / "deep-init" / "references" / "detection.md",
     "25 tree-sitter language grammars", "26 tree-sitter language grammars",
     "§35 detection.md reconciliation — must cite the verified 25-grammar Graphify count", "§35"),
    (PKG / "validation" / "STATS.json",
     '"naive_fp_avoided_total": 90', '"naive_fp_avoided_total": 91',
     "§36 stats byte-stable — STATS.json must regenerate from the records (no hand-edit)", "§36"),
    (ROOT / "mini-graphify" / "registry.json",
     '"api": ["api"]', '"api": ["apiX"]',
     "§35 edge-resolution — the component registry mapping must drive the resolved skeleton", "§35"),
    (PKG / "skills" / "deep-init" / "SKILL.md",
     "name: deep-init", "name: deep-xnit",
     "§1 lint — SKILL.md frontmatter name must be deep-init", "§1"),
    # ── Phase-6 M3 deepening: the load-bearing families the first 6 missed ──
    (ROOT / "mini-redaction" / "ground-truth" / "expected.json",
     "AKIAIOSFODNN7EXAMPLE", "AKIANOTINSOURCE0000X",
     "§8 redaction — a planted secret must be DETECTED (a must_redact value absent from src ⇒ a leak)", "§8"),
    (ROOT / "mini-keepmarker" / "ground-truth" / "expected.json",
     "refactor the billing edge case next sprint.", "refactor the billing edge case NEXT YEAR.",
     "§17 owned-region — human spans must be preserved byte-for-byte (a span not in AGENTS.md ⇒ not preserved)", "§17"),
    (PKG / "validation" / "cost" / "kemalcr-kemal.json",
     '"est_usd": 8.25', '"est_usd": 8.26',
     "§33 cost-ledger — est_usd must recompute from the record's own tokens × dated price (no hand-edited $)", "§33"),
    (ROOT / "mini-if8-cycles" / "src" / "shipping" / "shipping.ts",
     "from '../orders/orders'", "from '../shared/shared'",
     "§21 IF-8 — the import-graph detector reads real imports (breaking the cycle-closing edge ⇒ no cycle)", "§21"),
    (ROOT / "_wave1_ledgers.json",
     '"line": 34, "symbol": "bulkDeleteOrders"', '"line": 134, "symbol": "bulkDeleteOrders"',
     "§18 semantic recall — a seeded IF-1 issue mis-located beyond tol must drop recall below 100%", "§18"),
    (ROOT / "_external_metamorphic_ledgers.json",
     "97e23ed1991e5297d43846d62e981d7fb0111476", "97e23ed1991e5297d43846d62e981d7fb0deadbe",
     "§26 external oracle — a ledger SHA mismatching the held-out key makes the target unscorable", "§26"),
    (ROOT / "mini-exclusion" / "repo" / ".gitignore",
     "secrets.env", "notthere.env",
     "§41 exclusion pass — a gitignored secret no longer matched is wrongly INCLUDED (category/count mismatch)", "§41"),
    # ── Phase-6 M7 deepening: the new M7-7/M7-8 gates (§43–§46) ──
    (PKG / "tools" / "build_docs_viewer.py",
     'blob = blob.replace("<", lt)', 'blob = blob.replace("Q", lt)',
     "§43 viewer escaping — disabling the '<' escape lets a doc's </script> break the JSON island (raw < in island)", "§43"),
    (PKG / "tools" / "db_gate.py",
     '"rds.amazonaws.com",        # AWS RDS / Aurora', '"rds.amazonaws.invalid",    # AWS RDS / Aurora',
     "§44 R7 host-classification — dropping the RDS managed-endpoint pattern wrongly ALLOWS a prod host", "§44"),
    (PKG / "tools" / "lean_placement.py",
     'deep.append(f["id"])', 'lean.append(f["id"])',
     "§45 R9 lean-tier — routing an ISS- defect to the lean tier (instead of deep) violates R9 and must be caught", "§45"),
    (PKG / "tools" / "issue_config.py",
     'if (e_fam in ("*", fam))', 'if (e_fam in (fam,))',
     "§46 config — dropping the '*' wildcard match lets a vendored IF-8 candidate wrongly FIRE", "§46"),
    # ── M8-T3 deepening: a killing mutation for every remaining load-bearing oracle family ──
    (ROOT / "mini-if7a-errorrule" / "ground-truth" / "expected.json",
     '"certainty": "MEDIUM"', '"certainty": "HIGH"',
     "§27 IF-7(a) certainty cap — an expected issue at HIGH violates the ≤MEDIUM semantic-inference rule", "§27"),
    (ROOT / "mini-if6-enumforms" / "src" / "payments" / "enums.ts",
     "export enum Priority { Low, High }", "export enum Priority { Low, Med, High }",
     "§28 IF-6 named-set — making payments.Priority match billing removes the divergence (set-diff must stop firing)", "§28"),
    (ROOT / "mini-if10-crossmod" / "src" / "flagdefs" / "defs.ts",
     "export const NEW_CHECKOUT = false;", "export const NEW_CHECKOUT = flag;",
     "§29 IF-10 xmod — a non-literal RHS breaks the resolve-to-literal fold (E1 can no longer ground-fire)", "§29"),
    (ROOT / "mini-if10-crossmod" / "src" / "pyflags" / "defs.py",
     "NEW_CHECKOUT = False", "NEW_CHECKOUT = flag",
     "§30 IF-10 py — a non-literal RHS breaks the Python cross-package fold (E1py can no longer ground-fire)", "§30"),
    (ROOT / "mini-conformance-census" / "ground-truth" / "expected.json",
     '"signal": "CORROBORATE"', '"signal": "STALE"',
     "§31 census — the ADR-100 census signal must match the computed (N,k) arithmetic (CORROBORATE, not STALE)", "§31"),
    (PKG / "validation" / "results" / "kemalcr-kemal.json",
     '"naive_detector_false_positives": 12', '"naive_detector_false_positives": 13',
     "§32 precision — naive-FP must equal N−k (a hand-edited naive count breaks arithmetic-consistency)", "§32"),
    (PKG / "skills" / "deep-init" / "references" / "detection.md",
     "extraction_ladder.skipped", "extraction_ladder.xkipped",
     "§37 exclusion-pass spec — detection.md must specify the honesty-counting requirement (skipped totals)", "§37"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "--emit-windsurf", "--emit-xindsurf",
     "§38 projection coverage — generation.md must specify each agent-tool projection emit flag", "§38"),
    (PKG / "skills" / "deep-init" / "references" / "detection.md",
     "Selective activation", "Xelective activation",
     "§39 selective-activation — detection.md must specify the right-size-the-profile (D3) behavior", "§39"),
    (PKG / "validation" / "end-to-end" / "kemal" / "_e2e_record.json",
     '"verification_refuted": 0', '"verification_refuted": 1',
     "§40 canonical e2e — a refuted citation breaks the archived all-resolved-0-refuted invariant", "§40"),
    (PKG / "validation" / "_baseline.json",
     '"precision_false_defects": "== 0"', '"precision_false_defectsX": "== 0"',
     "§42 frozen baseline — the declared never-regress invariants must match the set the gate enforces", "§42"),
    (PKG / "skills" / "deep-init" / "SKILL.md",
     "  - Glob", "  - WebFetch",
     "§47 no-egress — a network tool (WebFetch) in allowed-tools must be detected (the skill has no egress path)", "§47"),
    (ROOT / "mini-edge-cases" / "repo" / "src" / "gen_header.ts",
     "// @generated by some-codegen-tool. DO NOT EDIT.", "// an ordinary first-party comment line.",
     "§48 edge-robustness — stripping the @generated/DO-NOT-EDIT markers must reclassify the file as source", "§48"),
    (PKG / "tools" / "graphify_adapter.py",
     "continue  # intra-component edge: not a cross-component dependency",
     "pass  # intra-component edge: not a cross-component dependency",
     "§49 property — emitting an intra-component edge violates the no-self-edge property (the fuzz catches it)", "§49"),
    (PKG / "tools" / "graphify_adapter.py",
     'is_call = ctx == "call" or rel in _CALL_RELATIONS',
     'is_call = False  # MUTANT: drop the v2 call edge class',
     "§100 v2 edge class — disabling calls capture must drop calls_into/called_by (the harvested-call gate is load-bearing)", "§100"),
    (PKG / "tools" / "graphify_adapter.py",
     "runtime_backed = True",
     "runtime_backed = False  # MUTANT: never confirm a runtime cycle",
     "§101 IF-8 classify — never tagging a cycle runtime_backed must fail the runtime-vs-type-only gate", "§101"),
    (PKG / "skills" / "deep-init" / "references" / "update.md",
     "rebuild the structural graph (deterministic, 0-token)",
     "note the structural graph stays as-is",
     "§102 refresh-rebuild — dropping Step 0b's graph rebuild from --update must fail the refresh-rebuild spec gate", "§102"),
    (PKG / "tools" / "build_report.py",
     'classes = ["imports"]',
     'classes = ["imports", "calls"]  # MUTANT: claim calls even when absent',
     "§103 provenance — fabricating a 'calls' edge class the graph doesn't have must fail the honest-scope gate", "§103"),
    (PKG / "tools" / "graphify_adapter.py",
     "if symbol in ((c.get(cls) or {}).get(component) or []):",
     "if ((c.get(cls) or {}).get(component) or []):  # MUTANT: ignore the symbol (no narrowing)",
     "§104 DP-1 narrowing — ignoring the symbol (re-marking the whole closure) must fail the symbol-precision gate", "§104"),
    (PKG / ".ai" / "docs" / "decisions.md",
     "harvests the native AST relations only",
     "builds the enriched reflection layer",
     "§105 Tier-5 finding — inverting the native-only stance (claiming we build the enriched reflection) must fail the recorded-DEFER gate", "§105"),
    (PKG / "validation" / "end-to-end" / "kemal" / "_golden_snapshot.json",
     '"sarif_result_count": 0', '"sarif_result_count": 1',
     "§50 golden snapshot — a drifted structural fingerprint (sarif result count) must fail the golden gate", "§50"),
    (ROOT / "mini-global-rules" / "bad" / "r1_ungrounded.md",
     "- BR-bill:002 The billing subsystem is generally secure and well-structured",
     "- BR-bill:002 The billing subsystem is secure [HIGH] (src/billing/sec.ts:1)",
     "§51 global-rules R1 — if the ungrounded-claim negative control is grounded, the R1 gate must notice it stopped catching", "§51"),
    (PKG / "tools" / "verify_citations.py",
     "elif a < 1 or b > n:", "elif a < 1 or b > n + 9999:",
     "§56 citation verifier — disabling the out-of-range line check lets a broken citation pass (must be caught)", "§56"),
    (ROOT / "mini-multicomponent" / "ground-truth" / "expected.json",
     '"nested": ["auth", "billing"]', '"nested": ["auth"]',
     "§59 emit oracle — dropping a substantial component from the expected nested set must break the emit-completeness manifest gate", "§59"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "≥ 2 source files OR ≥ 200 source lines", "substantial enough",
     "§59 engine-fix — reverting generation.md to the vague 'substantial enough' (no objective threshold) must re-RED the emit-completeness spec gate", "§59"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "the repo has **≥ 2 components**", "the repo has some components",
     "§59 condition-1 — dropping the '≥ 2 components' condition from the nested rule must re-RED G4 (each condition independently guarded)", "§59"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "the component **owns its own directory**", "the component is present",
     "§59 condition-2 — dropping the 'owns its own directory' condition must re-RED G4", "§59"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "≥ 1 non-obvious lean finding", "≥ 0 facts",
     "§59 condition-4 — dropping the 'non-obvious lean finding' condition must re-RED G4", "§59"),
    (PKG / "tools" / "emit_plan.py",
     "MIN_SOURCE_LINES = 200", "MIN_SOURCE_LINES = 99999999",
     "§59 emit-logic — disabling the source-lines OR-arm wrongly skips a 1-file/≥200-line component (fixture 'fatmodule'); G1 must catch it", "§59"),
    (PKG / "tools" / "emit_plan.py",
     'comp.get("has_own_dir", False)', 'comp.get("has_own_dir", True)',
     "§59 fail-safe — reverting the has_own_dir default to True silently emits a nested file for a dir-less component (fixture 'noflag'); G1/G2/G3 must catch it", "§59"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "Conditional cross-tool", "Optional cross-tool",
     "§59 front-door-model — removing the 'Conditional cross-tool AGENTS export' framing must re-RED §59 G7 (the canonical CLAUDE.md model; a UNIQUE phrase, since the model is stated redundantly elsewhere)", "§59"),
    (PKG / "skills" / "deep-init" / "references" / "detection.md",
     "Existing agent-file reconcile", "Existing agent-file summary",
     "§60 reconcile-detection — removing the agent-file reconcile detection from detection.md must re-RED G4", "§60"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "DeepInit OWNS this front door", "DeepInit shares this front door",
     "§60 reconcile-G1 — softening the UNIQUE primary front-door statement must re-RED §60 G1 (the review found G1's other substrings were non-unique → un-killable by a single-point mutation)", "§60"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "`CLAUDE.local.md` is explicitly NOT the shared file", "the local file is also shared",
     "§61 gitignore-mirror — dropping the CLAUDE.local.md exclusion (treating the personal-local file as shared) must re-RED G2", "§61"),
    (PKG / "tools" / "emit_projections.py",
     'or re.search(r"\\bRun\\s+(\\S+)", prov)', "or None",
     "§57 run_id-parse (B5) — disabling the pipe-header Run-id fallback regresses to 'run-unknown'; §57 G6 must catch it", "§57"),
    (PKG / "tools" / "emit_plan.py",
     'return False, "not_needed"', 'return True, "not_needed"',
     "§59 canonical-model — making a Claude-native run ALWAYS emit the redundant root AGENTS export must re-RED G1/G7 (front-door model)", "§59"),
    (PKG / "tools" / "backup_context.py",
     "return ordered[: len(ordered) - keep]", "return []",
     "§62 B2-prune — disabling the prune (never deleting old backups) must re-RED G4/G6 (non-accumulating backup)", "§62"),
    (PKG / "tools" / "backup_context.py",
     'r"AKIA[0-9A-Z]{16}"', 'r"AKIA_NOPE[0-9A-Z]{16}"',
     "§62 B2-redact — breaking the AWS-key secret pattern lets a planted secret pass into a backup; G3/G6 must catch it", "§62"),
    # ── 2026-06-15 dogfood fixes: B2 last-1 retention, ISS-005 canonical fallback, LESSON 1/1b citation rules ──
    (PKG / "tools" / "backup_context.py",
     "DEFAULT_KEEP = 1", "DEFAULT_KEEP = 9",
     "§62 B2-retention — reverting the default retention above last-1 (keeping a PILE of dated backups) must re-RED the last-1-default gate (G5)", "§62"),
    (PKG / "tools" / "emit_projections.py",
     '_CANONICAL_PREFERENCE = ("AGENTS.md", "CLAUDE.md")', '_CANONICAL_PREFERENCE = ("AGENTS.md",)',
     "§57 canonical-fallback (ISS-005) — dropping the CLAUDE.md fallback makes build_projections raise on a Claude-native (no-AGENTS.md) archive; §57 G7 must catch it", "§57"),
    (PKG / "tools" / "verify_citations.py",
     "if len(cands) == 1:", "if len(cands) == 0:",
     "§56 normalize-unique (LESSON 1) — disabling the unique-basename normalization leaves a bare citation unresolved; §56 G4 must catch it", "§56"),
    (PKG / "tools" / "verify_citations.py",
     "elif len(cands) > 1:", "elif len(cands) > 999:",
     "§56 normalize-ambiguous (LESSON 1) — dropping the ambiguous-bare branch silently mis-resolves a same-named file instead of flagging it; §56 G5 must catch it", "§56"),
    (PKG / "tools" / "verify_citations.py",
     'SHIFTING_FILES = {"CHANGELOG.md", "STATS.json"}', "SHIFTING_FILES = set()",
     "§56 shifting-line-cite (LESSON 1b) — emptying the shifting-files set stops flagging a line-cite into a regenerated file (CHANGELOG.md); §56 G6 must catch it", "§56"),
    (PKG / "skills" / "deep-init" / "references" / "verification.md",
     "MUST be a **full repo-relative path**", "MAY be a bare basename",
     "§56 spec (LESSON 1) — softening verification.md's full-repo-relative-path mandate (a UNIQUE sentence — the phrase alone recurs) must re-RED the citation-rule spec gate (§56 G7)", "§56"),
    # ── Tier-1 update-mechanism correctness (T1.1 grep-path completeness, T1.2 symmetric set-diff) ──
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "Completeness reconciliation (grep path)", "Surface notes (grep path)",
     "§63 completeness-spec (T1.1) — removing the grep-path completeness rule (the missed-propagation guard) must re-RED §63 G0", "§63"),
    (PKG / "skills" / "deep-init" / "references" / "update.md",
     "**symmetric set-diff**", "**one-pass scan**",
     "§64 set-diff-spec (T1.2) — removing the authoritative symmetric-set-diff rule (so deletions / the no-git path go unspecified) must re-RED §64 G0", "§64"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit_status.py",
     'return 1 if s["stale"] else 0', "return 0",
     "§65 status-exit (T2.0) — making the status keystone always exit 0 (never signalling stale) must re-RED §65 G3 (a hook/CI could not detect drift)", "§65"),
    (PKG / "skills" / "deep-init" / "SKILL.md",
     "`--auto-update=on|off` | **off**", "`--auto-update=on|off` | **on**",
     "§66 auto-update-default (T2.1) — reverting --auto-update to default-ON (the dishonest, token-spending default) must re-RED §66 G1 (the honesty fix)", "§66"),
    # ── Report (C-REPORT, §67) — the unified Docs+Insights artifact (ADR-019) ──
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     "/*__VENDOR_MARKDOWNIT__*/", "/*__VENDOR_GONE__*/",
     "§67 report-placeholder — removing the markdown-it vendored-inject placeholder must re-RED §67 G0", "§67"),
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     "function svgEl(", "fetch('x');function svgEl(",
     "§67 report-self-containment — a fetch() in the template must re-RED §67 G1 (no view-time network)", "§67"),
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     'data-mode="insights"', 'data-mode="insightsX"',
     "§67 report-view-switch — removing the Insights tab must re-RED §67 G2 (the merge)", "§67"),
    (PKG / "tools" / "build_report.py",
     "available = False", "available = True",
     "§67 report-honest-degrade — hardcoding risk.available=True must re-RED §67 G5 (R1: no fabricated zeros)", "§67"),
    # ── IF-5 risk metrics producer (manifest schema 4) — §19 reference-impl + §67 G6/G7 (this session) ──
    (PKG / "tools" / "risk_metrics.py",
     "CRIT_MULT = 1000", "CRIT_MULT = 100",
     "§19 risk-formula reference-impl — corrupting the 1000*CRIT weight in risk_metrics.py desyncs it from issues.md:115 (one source of truth); §19 must catch it", "§19"),
    (PKG / "tools" / "build_report.py",
     'float(m.get("risk", 0) or 0)', "0.0",
     "§67 report-value-propagation — hardcoding the risk read to 0.0 stops a real components.<name>.metrics value flowing to the Insights model; §67 G6 must catch it", "§67"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     '"schema_version": 4', '"schema_version": 3',
     "§67 metrics-producer-spec — reverting the manifest schema declaration to 3 (no schema-4 metrics block) must re-RED §67 G7", "§67"),
    # ── Command + parameter UX (§68) — the type-safe front door (tiered routing; this session) ──
    (PKG / "commands" / "check.md",
     'argument-hint: "[--status]"', 'arghint: "[--status]"',
     "§68 cmd-ux argument-hint — stripping the argument-hint from /deep-init:check hides its options in the / menu; §68 G2 must catch it", "§68"),
    (PKG / "commands" / "check.md",
     ".ai/deepinit_status.py", ".ai/deepinit_xtatus.py",
     "§68 cmd-ux non-lossy-merge — breaking the .ai/deepinit_status.py keystone invocation in /deep-init:check drops the 0-token status path; §68 G3 must catch it", "§68"),
    (PKG / "skills" / "deep-init" / "SKILL.md",
     "## Customize picker (interactive, opt-in", "## Picker (interactive, opt-in",
     "§68 cmd-ux picker — removing the documented 'Customize picker' question set (the type-safe button flow) must re-RED §68 G5", "§68"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit.config.schema.json",
     '"thorough", "deep"]', '"thorough", "deeep"]',
     "§68 cmd-ux schema — corrupting the depth enum in the config schema (editor type-safety) must re-RED §68 G6", "§68"),
    (PKG / "skills" / "deep-init" / "SKILL.md",
     "hidden alias", "documented alias",
     "§68 cmd-ux aliases — dropping a 'hidden alias' canonicalization note (so a duplicate alias pair is no longer deduped) must re-RED §68 G7", "§68"),
    # ── Version visibility (§69) — the loaded-version canary (version-agnostic finds; survive a bump) ──
    (PKG / "commands" / "version.md",
     "**DeepInit v", "**DeepInit v9",
     "§69 version canary-in-sync — a loaded-version literal that DISAGREES with plugin.json must re-RED §69 G1 (the canary can't lie)", "§69"),
    (PKG / "commands" / "version.md",
     "ONCE per session", "sometimes",
     "§69 version teaches-the-fix — dropping the 'loads ONCE per session' cache-truth must re-RED §69 G2", "§69"),
    (PKG / "tools" / "bump-version.mjs",
     "deepinit:loaded-version", "deepinit:loaded-xersion",
     "§69 version bump-sync — breaking the canary marker the bump tool keys on lets the literal silently drift; §69 G3 must catch it", "§69"),
    (PKG / "commands" / "plugin-update.md",
     "WAIT for an explicit yes", "run it immediately",
     "§69 upgrade confirm-gate — dropping the explicit-confirm guard (so /deep-init:plugin-update would auto-mutate host plugin state) must re-RED §69 G4", "§69"),
    (PKG / "commands" / "plugin-update.md",
     "**`/reload-plugins`**", "**the reload step**",
     "§69 upgrade reload-handoff — removing the /reload-plugins hand-off must re-RED §69 G5 (the loop can't silently drop the activation step)", "§69"),
    (PKG / "commands" / "version.md",
     "restart the IDE itself", "reload the window",
     "§69 reload host-adaptive — dropping the IDE-restart fallback from the version canary's stale branch (so the message wrongly implies /reload-plugins always suffices in the VS Code/JetBrains extension) must re-RED §69 G6", "§69"),
    # ── Host-adaptive upgrade/version (§69 G7–G10) — detect-host-first + firm restart truth + /plugin UI + refresh-first ──
    (PKG / "commands" / "version.md",
     "Detect your host", "Use the first host",
     "§69 host-detect G7 (version) — dropping the detect-your-host-first instruction (reverting to a flat all-hosts menu) must re-RED §69 G7", "§69"),
    (PKG / "commands" / "plugin-update.md",
     "Detect your host", "Use the first host",
     "§69 host-detect G7 (upgrade) — dropping the detect-your-host-first instruction must re-RED §69 G7", "§69"),
    (PKG / "commands" / "version.md",
     "does not reload the plugin host", "may not reload the plugin host",
     "§69 reload G8 (version) — softening the firm 'does not reload the plugin host' back to a 'may not' hedge must re-RED §69 G8", "§69"),
    (PKG / "commands" / "plugin-update.md",
     "does not reload the plugin host", "may not reload the plugin host",
     "§69 reload G8 (upgrade) — softening the firm 'does not reload the plugin host' back to a 'may not' hedge must re-RED §69 G8", "§69"),
    (PKG / "commands" / "plugin-update.md",
     "Plugins tab", "the menu",
     "§69 upgrade G9 extension-plugin-ui — dropping the /plugin Plugins-tab path (so the extension wrongly gets a bare-shell `claude` call) must re-RED §69 G9", "§69"),
    (PKG / "commands" / "plugin-update.md",
     "silently no-op", "always update",
     "§69 upgrade G10 silent-no-op-trap — removing the refresh-first / silent-no-op warning must re-RED §69 G10", "§69"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit.config.schema.json",
     '"default": "thorough"', '"default": "fast"',
     "§68 G8 scrutiny-dial — flipping the schema review default off thorough must re-RED §68 G8", "§68"),
    # ── Adaptive review escalation (§76; v0.31.0) — default self-escalates 2→3 on the cycle-2 gate; no force/cap knob ──
    (PKG / "skills" / "deep-init" / "references" / "review.md",
     "CRITICAL issues remaining > 0", "CRITICAL issues remaining > 9",
     "§76 review-adaptive G1 — corrupting the cycle-2 escalation gate condition in review.md (the adaptive 3rd-cycle CRITICAL trigger) must re-RED §76 G1", "§76"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit.config.schema.json",
     '"enum": ["fast", "thorough"]', '"enum": ["fast", "thorough", "aggressive"]',
     "§76 review-adaptive G2 — re-adding the retired `aggressive` mode to the review enum (a force-max knob removed for simplicity) must re-RED §76 G2 / §68 G6", "§76"),
    # ── Legacy viewer/dashboard deprecation → unified report (§70 redirect stub; ADR-019) — this session ──
    (PKG / "skills" / "deep-init" / "assets" / "legacy-stub-template.html",
     'href="report.html"', 'href="reportX.html"',
     "§70 legacy-stub link — breaking the stub's relative forward link to report.html (old bookmarks would 404) must re-RED §70 G1", "§70"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "[DEPRECATED → superseded by", "[Legacy note: superseded by",
     "§70 deprecation-stated — dropping ONE of the two '[DEPRECATED → superseded by report.html]' markers (a silent legacy removal) drops the count below 2 and must re-RED §70 G2", "§70"),
    # ── Component dependency graph (ITEM-2 presentation-only; §67 G8) — reads the existing structural-graph.json ──
    (PKG / "tools" / "build_report.py",
     '"from": n, "to": tgt', '"from": tgt, "to": n',
     "§67 graph-edges — reversing the import-edge direction in graph_from_structural corrupts the component graph (from↔to); §67 G8 must catch it", "§67"),
    # ── Interactive Map view (C-MAP, §75) — the navigable component graph (ADR-024) ──
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     'data-mode="map"', 'data-mode="mapX"',
     "§75 map-tab — renaming the Map view-mode token (data-mode=\"map\") removes the third top-level tab so the navigable graph view is unreachable; §75 G1 must catch it", "§75"),
    (PKG / "tools" / "build_report.py",
     '"anchor": "c-" + bdv._slug(n)', '"anchor": bdv._slug(n)',
     "§75 map-anchor — dropping the c- prefix on a Map node's component anchor breaks click-to-navigate (the node points at no real component route); §75 G2 must catch it", "§75"),
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     '<script>/*__VENDOR_CYTOSCAPE__*/</script>', '<script>/*__VENDOR_CYTOSCAPE_X__*/</script>',
     "§75 map-vendor-placeholder — renaming the Cytoscape inline placeholder means the graph lib is never bundled into the self-contained report (it would need a network load); §75 G3 must catch it", "§75"),
    (PKG / "tools" / "build_report.py",
     '"/*__VENDOR_CYTOSCAPE__*/": "cytoscape.min.js"', '"/*__VENDOR_CYTOSCAPE_X__*/": "cytoscape.min.js"',
     "§75 map-inline-sub — corrupting the Cytoscape VENDOR_SUBS key leaves the placeholder unsubstituted (the wrapped form survives in the output); §75 G4 must catch it", "§75"),
    # ── Multi-language report (C-I18N; §71) — the translation overlay mechanism (this session) ──
    (PKG / "tools" / "i18n_tokens.py",
     "out = out.replace(_sentinel(i), tok)", "out = out.replace(_sentinel(i), '')",
     "§71 token-restore — making restore() drop the protected span (insert '' instead of the token) breaks the mask/restore round-trip; §71 G1 must catch it", "§71"),
    (PKG / "tools" / "i18n_tokens.py",
     'lang or "", glossary_hash or ""', '"", glossary_hash or ""',
     "§71 content-key — dropping `lang` from the content key lets two languages collide on one cache entry; §71 G2 must catch it", "§71"),
    (PKG / "tools" / "build_i18n.py",
     "return s   # English fallback", "return ''  # English fallback",
     "§71 honest-degrade — returning '' instead of the English source on a TM miss/verify-fail fabricates a BLANK field (not the honest English fallback); §71 G3 must catch it", "§71"),
    (PKG / "tools" / "build_i18n.py",
     '"dir": "rtl"', '"dir": "ltr"',
     "§71 RTL — flipping Hebrew's dir to ltr drops right-to-left layout for he; §71 G4 must catch it", "§71"),
    (PKG / "tools" / "build_i18n.py",
     '"es": {"name": "Español"', '"eX": {"name": "Español"',
     "§71 shipped-set — corrupting a target language code (es→eX) desyncs LANGS from the trimmed shipped set {es, he}; §71 G5 must catch it", "§71"),
    (PKG / "tools" / "build_i18n.py",
     "if not code:", "if code not in LANGS:",
     "§71 on-demand-reject — re-introducing the hard reject (only LANGS allowed) breaks the other:<language> on-demand path (a dropped code raises again); §71 G10 must catch it", "§71"),
    (PKG / "skills" / "deep-init" / "references" / "i18n.md",
     "English is the canonical analysis output", "English is one analysis output",
     "§71 spec — softening the canonical-English/never-touched invariant in i18n.md must re-RED §71 G6", "§71"),
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     'he:{docs:"תיעוד"', 'he:{docX:"תיעוד"',
     "§71 chrome-completeness — renaming a STRINGS key in the Hebrew block (so 'docs' is undefined for he) leaves chrome half-translated; §71 G0 must catch it", "§71"),
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     "unicode-bidi:isolate", "unicode-bidi:normal",
     "§71 RTL-isolation — dropping the LTR isolation lets code/file:line/IDs mirror under dir=rtl (grounding reverses); §71 G7 must catch it", "§71"),
    (PKG / "skills" / "deep-init" / "SKILL.md",
     "## Translate picker", "## Translate section",
     "§71 command-surface — removing the documented 'Translate picker' flow (the language selection menu) must re-RED §71 G8", "§71"),
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     "if(e.target===d) d.close()", "if(e.target===window) d.close()",
     "§71 dialog-close — breaking the shortcuts-dialog backdrop-click close (the reported stuck-dialog fix) must re-RED §71 G9", "§71"),
    # ── Proactive freshness (SessionStart suggestion + status path/schema fix) ──
    (PKG / "skills" / "deep-init" / "assets" / "deepinit_status.py",
     "len(v) >= 32", "len(v) >= 999",
     "§72 status-flat-schema — breaking the flat {path: sha} parse (no value qualifies) makes the keystone find 0 files and silently report 'fresh'; §72 G0 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit_status.py",
     "if isinstance(x, (list, tuple)):", "if isinstance(x, (list, tuple, int)):",
     "§72 status-files-robustness — widening _iter_paths to accept an int (so `for rel in <int>` runs again) re-introduces the 'int object is not iterable' keystone crash; §72 G0c must catch it", "§72"),
    (PKG / "hooks" / "hooks.json",
     "session-start.sh", "session-startX.sh",
     "§72 hook-wiring — corrupting the SessionStart command path unwires the plugin-shipped freshness hook; §72 G1 must catch it", "§72"),
    # ── Proactive freshness, cadence + the type-safe control surface (this session) ──
    (PKG / "skills" / "deep-init" / "assets" / "deepinit.config.schema.json",
     '["session", "window", "always"]', '["session", "window"]',
     "§72 cadence-schema — dropping a notify-cadence enum value breaks the type-safe cadence control; §72 G4 must catch it", "§72"),
    (PKG / "tools" / "freshness_config.py",
     "if n < 0:", "if n < -999:",
     "§72 writer-validate — disabling the negative-number guard lets an invalid notify-window-hours through; §72 G5 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "session-start.sh",
     '[ "$last" = "$SID" ] && exit 0', '[ "$last" = "NOPE" ] && exit 0',
     "§72 session-dedup — breaking the session-id dedup re-nudges within the same session (spam); the §72 G6 e2e must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "SKILL.md",
     "the one narrow config-write exception (R-config)", "the routine config rewrite (R-config)",
     "§72 control-surface — softening the 'one narrow config-write exception' (so a run could write config) must re-RED §72 G7", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit_status.py",
     'verdict, why = "no", "disabled by "', 'verdict, why = "yes", "disabled by "',
     "§72 explain-verdict — flipping the disabled→silent verdict makes --explain lie about whether the nudge fires; §72 G8 must catch it", "§72"),
    # ── Proactive freshness, second event + imperative offer + change summary (this session) ──
    (PKG / "hooks" / "hooks.json",
     '"UserPromptSubmit"', '"UserPromptSubmitX"',
     "§72 ups-wiring — renaming the UserPromptSubmit hook key unwires the second freshness surface (no first-prompt re-offer / mid-session catch); §72 G9 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "session-start.sh",
     '"hookEventName": event', '"hookEventName": "SessionStart"',
     "§72 event-agnostic — hardcoding hookEventName back to SessionStart makes the UserPromptSubmit payload mis-named (Claude Code rejects its additionalContext); §72 G10 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit_status.py",
     "shown = paths[:limit]", "shown = paths[:0]",
     "§72 change-summary — slicing the changed-path list to empty makes the nudge show no files (count-only again); §72 G11 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "session-start.sh",
     "Your FIRST action in this turn", "Your LATER action in this turn",
     "§72 imperative-offer — softening the imperative FIRST-action offer to a later/optional one lets it lose to the user's first message again; §72 G12 must catch it", "§72"),
    # ── Proactive freshness, the less-naggy behavior change: window default + remember-declines (this session) ──
    (PKG / "skills" / "deep-init" / "assets" / "session-start.sh",
     'CADENCE="$(cfg notify-cadence window)"', 'CADENCE="$(cfg notify-cadence session)"',
     "§72 window-default — reverting the default cadence to session re-nudges in every new short session (the naggy old behavior); §72 G13 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit.config.schema.json",
     '"always"], "default": "window"', '"always"], "default": "session"',
     "§72 window-default-schema — flipping the schema's default cadence back to session loses the type-safe less-naggy default; §72 G4 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "session-start.sh",
     '[ "$_snz_now" -ne 0 ] && [ "$_snz_now" -lt "$_snz_exp" ] && exit 0',
     '[ "$_snz_now" -ne 0 ] && [ "$_snz_now" -lt 0 ] && exit 0',
     "§72 snooze-gate — neutering the snooze comparison makes a 'Not now' decline never silence the nudge (it re-asks anyway); §72 G14 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit_status.py",
     "expiry = int(time.time() + hours * 3600)", "expiry = int(time.time() - hours * 3600)",
     "§72 snooze-writer — writing a PAST expiry makes --snooze a no-op (the decline back-off never takes); §72 G14 must catch it", "§72"),
    (PKG / "skills" / "deep-init" / "assets" / "session-start.sh",
     'if status else "/deep-init:customize', 'if False  else "/deep-init:customize',
     "§72 decline-clause — dropping the --snooze command from the nudge payload leaves the agent no way to record the decline; §72 G14 must catch it", "§72"),
    (PKG / "tools" / "freshness_config.py",
     '_NUMERIC = {"notify-window-hours", "notify-snooze-hours"}', '_NUMERIC = {"notify-window-hours"}',
     "§72 snooze-managed — dropping notify-snooze-hours from the surgical writer's managed keys makes the decline back-off un-tunable/unvalidated; §72 G5 must catch it", "§72"),
    # ── Mutation-lock — torn-tree commit guard (the PID lockfile producer + the pre-commit guard) ──
    (PKG / "tools" / "mutation_lock.py",
     "return True   # fail-closed: an unparseable or empty PID BLOCKS",
     "return False  # fail-closed: an unparseable or empty PID BLOCKS",
     "§73 fail-closed — an unparseable/empty PID must BLOCK a commit (a torn lock must never pass); §73 G3 must catch it", "§73"),
    (PKG / "tools" / "mutation_lock.py",
     "return True   # a live holder is running the mutation harness",
     "return False  # a live holder is running the mutation harness",
     "§73 live-holder blocks — a live mutation-run PID must BLOCK a commit; §73 G1 must catch it", "§73"),
    (PKG / "tools" / "mutation_lock.py",
     'f.write(f"{os.getpid()}',
     'f.write(f"x{os.getpid()}',
     "§73 PID-first-line — the lock's first line must be exactly the writer PID; §73 G4 must catch it", "§73"),
    (PKG / ".husky" / "pre-commit",
     "tools/mutation_lock.py",
     "tools/mutation_lockX.py",
     "§73 hook wiring — the pre-commit guard must invoke the mutation_lock helper; §73 G5 must catch it", "§73"),
    # ── Emit-time existing-file confirmation (§74, B3-confirm) — the no-improvised-prompt fix ──
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "The recommended option is ALWAYS the stated default",
     "The recommended option may differ from the stated default",
     "§74 emit-confirm-spec — softening the recommended==default anti-contradiction rule in generation.md (the self-contradicting-prompt fix) must re-RED §74 G0", "§74"),
    (PKG / "tools" / "emit_plan.py",
     'EXISTING_RECOMMENDED = "extend"', 'EXISTING_RECOMMENDED = "skip"',
     "§74 emit-confirm-logic — pointing the recommended option away from the 'extend' default (the exact dogfood bug: recommended != default) must re-RED §74 G1", "§74"),
    (PKG / "skills" / "deep-init" / "references" / "global-rules.md",
     "The recommended choice MUST equal the stated default",
     "The recommended choice may vary from the stated default",
     "§74 R10-guardrail — softening R10's recommended==default mandate (so a confabulated/self-contradicting prompt is no longer forbidden) must re-RED §74 G2", "§74"),
    (PKG / "skills" / "deep-init" / "assets" / "deepinit.config.schema.json",
     '"side-file"', '"side-xile"',
     "§74 side-file-real — corrupting the 'side-file' strategy in the config schema (so the 'Preview beside it' option maps to no real path) must re-RED §74 G3", "§74"),
    # ── Timing-instrumentation layer (§33 G10) — a hand-typed derived figure must not silently rot ──
    (PKG / "validation" / "cost" / "_schema-example-ledger.json",
     '"loc_per_sec": 21.19', '"loc_per_sec": 99.99',
     "§33 G10 processing-honesty — a cost.processing throughput figure that no longer recomputes from the record's own loc/wall must re-RED §33 G10 (the §33-G4 honesty extended to timing)", "§33"),
    # ── Integration run-record machinery (§77) — a drifted snapshot artifact must not pass ──
    (ROOT / "mini-integration-record" / "good.json",
     "13773ca8402a50137bc0ef1869c25ae270096bf4303d92d5d7ceeb2a0446ff4f",
     "0000000000000000000000000000000000000000000000000000000000000000",
     "§77 G3 artifact-hash integrity — a recorded snapshot hash that no longer matches the committed file (a drifted/torn snapshot) must re-RED §77 G3", "§77"),
    # ── IF-5 risk_metrics behavioral property (§78) — the bus-factor bonus is ==1-only ──
    (PKG / "tools" / "risk_metrics.py",
     "if bus_factor == 1:", "if bus_factor:",
     "§78 G4 bus-factor bonus — relaxing the ==1 test to a truthiness check (so bus_factor 2 wrongly earns the +50) must re-RED §78 G4", "§78"),
    # ── Citation-verifier EOF boundary (§79) — line n+1 must be out-of-range ──
    (PKG / "tools" / "verify_citations.py",
     "elif a < 1 or b > n:", "elif a < 1 or b > n + 1:",
     "§79 G1 EOF off-by-one — loosening the upper line bound so a cite one line past EOF wrongly resolves must re-RED §79 G1", "§79"),
    # ── Aggregator-producer round-trip (§80) — a hand-edited cost_model figure must not survive ──
    (PKG / "validation" / "matrix" / "cost_model.json",
     '"kemal_actual_over_base": 14.32', '"kemal_actual_over_base": 99.99',
     "§80 G1 cost-model round-trip — a hand-edited cost_model.json figure that build_cost_model.build() no longer regenerates must re-RED §80 G1", "§80"),
    # ── Stage-timing emission spec (§81) — generation.md must spec the time_source honesty ladder ──
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "engine_stage_stamps", "engine_DROPPED_stamps",
     "§81 G1 emit-spec — dropping the engine_stage_stamps rung from generation.md's time_source honesty ladder must re-RED §81 G1", "§81"),
    # ── Owned-region idempotency (§82) — the dated backup set must stay bounded (no accumulation) ──
    (PKG / "tools" / "backup_context.py",
     "return ordered[: len(ordered) - keep]", "return ordered[: len(ordered) - keep - 1]",
     "§82 G2 no-accumulation — an off-by-one in prune (keeps one extra backup each run → the pile grows) must re-RED §82 G2", "§82"),
    # ── Timing/integration aggregator spine (§83) — STATS.timing must regenerate from build_timing() ──
    (PKG / "validation" / "STATS.json",
     "no cost.processing timing blocks committed yet", "no cost.processing timing blocks committed SOON",
     "§83 G1 byte-stable — a hand-edited STATS.timing block that build_timing() no longer regenerates must re-RED §83 G1", "§83"),
    # ── Integration auditor (§84) — the auditor must RE-DERIVE, never trust the record's self-reported claims ──
    (PKG / "tools" / "audit_integration_run.py",
     '"ok": all(c["ok"] for c in checks),', '"ok": True,',
     "§84 G2 re-derivation — making the auditor always pass (trusting the record instead of recomputing) must re-RED §84 G2", "§84"),
    # ── Tier-2 runner static contract (§85 / §A4) — inverting the env-guard makes the metered driver fire in CI ──
    (PKG / "tools" / "run_integration.py",
     'get(REAL_ENGINE_ENV) != "1"', 'get(REAL_ENGINE_ENV) == "1"',
     "§85 G1 env-guard — inverting the DEEPINIT_REAL_ENGINE guard (the runner would fire WITHOUT the flag, spend tokens in CI, and no-op WITH it) must re-RED §85 G1", "§85"),
    # ── Multi-repo e2e snapshot (§86 / §A3) — a CDN <script> in a snapshot dashboard breaks self-containment ──
    (PKG / "tests-fixtures-v1" / "mini-e2e-snapshot" / ".ai" / "dashboard.html",
     "</body>", '<script src="https://cdn.jsdelivr.net/npm/x.js"></script>\n</body>',
     "§86 G2 self-containment — planting an external CDN <script src=https://…> in a snapshot dashboard (it no longer opens offline) must re-RED §86 G2", "§86"),
    # ── Per-run scorecard (§87 / §C9) — injecting a deepinit_wrong∧HIGH row must trip the hard wrong-HIGH==0 gate ──
    (PKG / "tests-fixtures-v1" / "mini-scorecard" / "good.json",
     '"deepinit_wrong_high": 0', '"deepinit_wrong_high": 2',
     "§87 G2 hard-gate — injecting a confident code-refuted fact (deepinit_wrong∧HIGH row) into a scored run must trip the wrong_high==0 rollup gate (R1 cardinal sin) and re-RED §87 G2", "§87"),
    # ── Coverage non-regression floors (§88 / §C10) — a current run dropping below a frozen floor must be caught ──
    (PKG / "tests-fixtures-v1" / "mini-coverage-floor" / "good.json",
     '"pct": 0.7292', '"pct": 0.40',
     "§88 G2 coverage-floor — lowering a current run's pooled coverage below the frozen _baseline floor (a spec edit that silently dropped coverage) must re-RED §88 G2", "§88"),
    # ── Mirror replay oracle (§89 / §C11) — a flipped adjudication bucket must make the deterministic re-score diverge ──
    (PKG / "tests-fixtures-v1" / "mini-coverage-record" / "good.json",
     '"bucket": "MATCH"', '"bucket": "MISS"',
     "§89 G2 rescore — flipping a MATCH adjudication bucket to MISS makes the committed scores no longer reproduce from the record's own adjudication (a tampered/regressed run); the replay oracle must re-RED §89 G2", "§89"),
    # ── Update isolation (§90 / §C7) — broadening the insert scope wipes unchanged sibling keys ──
    (PKG / "tools" / "freshness_config.py",
     "% (key, literal, inner)", "% (key, literal, '')",
     "§90 G1 update-isolation — dropping the preserved prior content (inner) from the surgical front-insert wipes every unchanged sibling key when a new key is added; §90 G1 must catch the lost isolation", "§90"),
    # ── Redaction adversarial (§91 / §C8) — dropping the quoted-key handling lets a JSON-quoted credential leak ──
    (PKG / "tools" / "backup_context.py",
     r'''(["']?\s*[=:]\s*)''', r'''(\s*[=:]\s*)''',
     "§91 G2 redaction — reverting the quoted-key separator lets the JSON/YAML \"password\": \"secret\" form slip past redaction (the `\"` between key and colon blocks the bare pattern); §91 G2 must catch the leak", "§91"),
    # ── IF-1 FP-trap (§92 / §C6) — relaxing a documented-exception reason (dropping its suppression mechanism) ──
    (PKG / "tests-fixtures-v1" / "mini-if1-fptrap" / "ground-truth" / "expected.json",
     "APPEND-ONLY audit log (frozen records), never a mutation of an owned order, so the owner-only rule does not apply; suppress.",
     "was overlooked by the author here.",
     "§92 G1 if1-fptrap — relaxing a must_not_fire reason so it no longer cites a documented suppression mechanism (an ungrounded FP-trap) must re-RED §92 G1 (and the global §14 semantic check)", "§92"),
    # ── IF-10 Go port (§93 / §C5) — a non-literal const RHS must break the resolve-to-literal fold (no fire) ──
    (PKG / "tests-fixtures-v1" / "mini-if10-crossmod-go" / "flags" / "flags.go",
     "const NewCheckout = false", "const NewCheckout = isEnabled()",
     "§93 G1 IF-10-go — a non-literal const RHS (a call, not a true/false/int/string literal) is no longer resolved by the Go fold, so the cross-module dead-branch fire vanishes; §93 G1 must catch the lost fire", "§93"),
    # ── Marketing-figure dormancy (§94 / M8) — removing the publishable_figure_ready gate publishes figures unmeasured ──
    (PKG / "tools" / "check_stats_drift.py",
     'if not timing.get("publishable_figure_ready"):', "if False:",
     "§94 G1 marketing-figure — removing the publishable_figure_ready gate makes timing_figure_checks() activate the 4 marketing-figure guards with NO metered data (publishing a fabricated figure); §94 G1 must catch the lost dormancy", "§94"),
    # ── §95–§97: the R10-plain run-start prompt family (no jargon · consolidated/ask-once · plain DB card) ──
    (PKG / "tools" / "prompt_ux.py",
     '("Faster, lighter pass", "fast")', '("Faster pass depth=fast", "fast")',
     "§95 R10-plain — a raw parameter token (depth=) reaching a prompt option label must be caught by the banned-term scan (§95 G3)", "§95"),
    (PKG / "tools" / "prompt_ux.py",
     'COST_RECOMMENDED = "proceed"', 'COST_RECOMMENDED = "cancel"',
     "§96 run-start — the scope/effort card's recommended option must equal the full-deep default; a recommendation that fights the default violates R10 (§96 G3)", "§96"),
    (PKG / "tools" / "db_gate.py",
     '"live_offered": decision == "allow",', '"live_offered": True,',
     "§97 db-card — a production / managed-cloud host must be auto-declined to code-only (live_offered False); offering it as a live target violates the R7 safety bias (§97 G2)", "§97"),
    # ── Progress presentation (§98) — the deterministic % bar weights + the honest range-or-None ETA ──
    (PKG / "tools" / "progress_model.py",
     '"extract": 0.45,', '"extract": 0.55,',
     "§98 G1 stage-weights — a STAGE_WEIGHTS value that no longer lets the full-run weights sum to exactly 1.0 must re-RED §98 G1 (the % bar would mis-scale)", "§98"),
    (PKG / "tools" / "progress_model.py",
     "return (round(lo * remaining, 1), round(hi * remaining, 1))",
     "return round(hi * remaining, 1)",
     "§98 G3 eta-range — making eta_range return a single number instead of a (lo,hi) range (a fabricated precise countdown) must re-RED §98 G3 (R1: an honest range or an omission, never a bare number)", "§98"),
    (PKG / "tools" / "build_report.py",
     '"duration_sec": (float(dur) if dur is not None else None)',
     '"duration_sec": None',
     "§98 G7 report-timing-data — dropping the per-stage duration propagation in build_timing_panel (so the Insights timing panel shows no real durations) must re-RED §98 G7", "§98"),
    (PKG / "skills" / "deep-init" / "assets" / "report-template.html",
     "pg.appendChild(timingCard(dash));", "pg.appendChild(severityCard(dash));",
     "§98 G8 report-timing-template — unwiring the timingCard from the Insights panel grid (so the 'where the time went' panel never renders) must re-RED §98 G8", "§98"),
    # ── Shared-state write-conflict SUBSTRATE (P1 matrix + P2 external-actor inference) + the SARIF helpUri fix ──
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "blob/main/skills/deep-init/references/issues.md", "blob/main/skill/references/issues.md",
     "substrate-P1P2 §15 SARIF helpUri — reverting the rule helpUri to the legacy singular skill/ path (a 404 in emitted SARIF) must re-RED the SARIF-hygiene gate", "§15"),
    (PKG / "skills" / "deep-init" / "references" / "horizontal.md",
     "write-conflict correlation", "write-conflict ZZZ-removed",
     "substrate-P1P2 §99 G1 — removing the 'write-conflict correlation' matrix label from horizontal.md §3e must re-RED §99 G1", "§99"),
    (PKG / "skills" / "deep-init" / "references" / "horizontal.md",
     "semantic judgements", "structural reads",
     "substrate-P1P2 §99 G2 — re-tiering compound/asymmetric from 'semantic judgements' to structural must re-RED §99 G2 (the central correctness fix vs the proposal)", "§99"),
    (PKG / "skills" / "deep-init" / "references" / "horizontal.md",
     "no new all-pairs", "no new per-component",
     "substrate-P1P2 §99 G3 — dropping the 'no new all-pairs' scope-honesty claim must re-RED §99 G3 (R2-faithful, no fresh scan)", "§99"),
    (PKG / "skills" / "deep-init" / "references" / "generation.md",
     "six whole-system horizontal docs", "five whole-system horizontal docs",
     "substrate-P1P2 §99 G4 — reverting the Emit-completeness list to 'five' (6th doc unregistered) must re-RED §99 G4", "§99"),
    (PKG / "tools" / "emit_plan.py",
     '"shared-state-conflicts.md",', '"shared-state-conflicts-MUTATED.md",',
     "substrate-P1P2 §99 G5 — corrupting the emit_plan HORIZONTAL_DOCS doc name must re-RED §99 G5 + §59 G1/G6 (oracle↔spec lock-step)", "§99"),
    (PKG / "skills" / "deep-init" / "references" / "extraction.md",
     "(Q13)", "(Q99)",
     "substrate-P1P2 §99 G6 — removing the Q13 external-actor inference question must re-RED §99 G6", "§99"),
    (PKG / "skills" / "deep-init" / "references" / "extraction.md",
     "file-IO/email/external-actor", "file-IO/email",
     "substrate-P1P2 §99 G7 — dropping the additive external-actor IP type must re-RED §99 G7", "§99"),
    # ── ISS-010 parser unification: the ONE tolerant build_docs_viewer parser handles the dogfood ledger shape ──
    (PKG / "tools" / "build_docs_viewer.py",
     r"^##\s+(ISS-[\w:.\-]+)\s+[—-]\s+", r"^###\s+(ISS-[\w:.\-]+)\s+[—-]\s+",
     "ISS-010 §43 G6 dogfood-issue-arm — requiring ### instead of ## stops the top-level '## ISS-NNN —' "
     "ledger shape parsing (the shape DeepInit emits); §43 G6 must catch it", "§43"),
    (PKG / "tools" / "build_docs_viewer.py",
     r"^###\s+(ADR-\d+)\s+[—-]\s+", r"^###\s+(ADR-\d+):\s+",
     "ISS-010 §43 G6 dogfood-adr-arm — requiring a colon instead of the em-dash misses the '### ADR-N —' "
     "shape DeepInit emits (the canonical ADR parse regresses to empty); §43 G6 must catch it", "§43"),
]


def run_harness() -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(HARNESS)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**_env()})
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _env():
    import os
    e = dict(os.environ); e["PYTHONUTF8"] = "1"; return e


def main() -> int:
    # Optional SUBSET selection (a full run is one harness pass per mutation — slow; chunking keeps each
    # invocation fast/foreground). No args ⇒ run ALL (the default contract is unchanged). Coverage stats +
    # build_stats' mutation_count always read the full MUTATIONS list, so a subset run never skews them.
    import argparse
    ap = argparse.ArgumentParser(description="DeepInit mutation meta-harness (subset flags are for fast chunked runs).")
    ap.add_argument("--only", help="run only mutations whose label or section contains this substring")
    ap.add_argument("--start", type=int, default=0, help="index of the first mutation to run")
    ap.add_argument("--count", type=int, default=None, help="how many mutations to run from --start")
    ap.add_argument("--changed", action="store_true",
                    help="run only mutations whose TARGET file changed vs HEAD — the L1 'gate' layer "
                         "(fast pre-commit subset; see docs/TESTING.md). Empty set ⇒ nothing to re-verify.")
    args = ap.parse_args()
    _selected = [m for m in MUTATIONS if (args.only is None) or (args.only in m[3]) or (args.only in m[4])]
    if args.changed:
        # L1 GATE: only re-verify mutations whose target file is in `git diff --name-only HEAD` (the files
        # about to be committed). Keeps the per-commit gate fast; the full sweep stays L2 (validate_all).
        try:
            _ch = subprocess.run(["git", "-C", str(PKG), "diff", "--name-only", "HEAD"],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
            _changed_set = {ln.strip() for ln in _ch.stdout.splitlines() if ln.strip()}
        except Exception:
            _changed_set = set()
        def _rel(fp):
            try: return Path(fp).resolve().relative_to(PKG).as_posix()
            except Exception: return None
        _selected = [m for m in _selected if _rel(m[0]) in _changed_set]
    _selected = _selected[args.start: (args.start + args.count) if args.count is not None else None]
    # Keyless (public) build: the held-out external-oracle key (_external/_external_keys.json) is not shipped, so
    # §26 inert-skips in the suite — its mutation can never be killed (the gate it targets isn't running). Drop the
    # key-dependent mutation(s) from the sweep when the key is absent, so a public clone's mutation gate stays green.
    # (Internally, where the held-out key is present, §26's mutation runs and kills as before.)
    _keyless = bool(os.environ.get("DEEPINIT_PUBLIC_HARNESS")) or not (ROOT / "_external" / "_external_keys.json").exists()
    if _keyless:
        _selected = [m for m in _selected if m[4] != "§26"]
    _subset = len(_selected) != len(MUTATIONS)

    # Hold the torn-tree commit lock for the WHOLE run (a planted mutation must never be committable).
    # acquire() writes <repo>/.oss-kit/.mutation-running with our PID + registers atexit/SIGINT/SIGTERM cleanup;
    # the lock is released only on exit (NOT in a finally), so it covers the final clean restore-run below too.
    sys.path.insert(0, str(PKG / "tools"))
    import mutation_lock
    mutation_lock.acquire(PKG)
    print("══ mutation-testing the DeepInit validation suite ══"
          + (f"  [SUBSET: {len(_selected)}/{len(MUTATIONS)}]" if _subset else "") + "\n")

    # BASELINE-GREEN precheck
    rc, out = run_harness()
    if rc != 0:
        print("BASELINE NOT GREEN — fix the suite before mutation-testing. Last lines:")
        print("\n".join(out.strip().splitlines()[-5:]))
        return 2
    base_total = _result_count(out)
    print(f"baseline: GREEN ({base_total})\n")

    killed, survived, stale = [], [], []
    for fp, find, repl, label, section in _selected:
        if not fp.exists():
            stale.append((label, f"file missing: {fp.relative_to(PKG)}")); continue
        original = fp.read_bytes()
        text = original.decode("utf-8")
        if find not in text:
            stale.append((label, f"find-string absent in {fp.relative_to(PKG)}: {find!r}")); continue
        try:
            fp.write_text(text.replace(find, repl, 1), encoding="utf-8")
            rc, out = run_harness()
        finally:
            fp.write_bytes(original)   # ALWAYS restore, even on exception
        if rc != 0:
            # KILLED. Bonus: did the EXPECTED section report a FAIL?
            hit = _section_failed(out, section)
            killed.append((label, section, hit))
            print(f"  [KILLED] {label}\n            → harness went RED" + (f" ({section} FAILED)" if hit else f" (a check failed; not pinned to {section})"))
        else:
            survived.append((label, section))
            print(f"  [SURVIVED] {label}\n            → harness STAYED GREEN despite the mutation — VACUOUS CHECK in {section}!")

    print("\n" + "═" * 52)
    print(f"  mutations: {len(killed)} KILLED · {len(survived)} SURVIVED · {len(stale)} STALE (of {len(MUTATIONS)})")
    for label, why in stale:
        print(f"  [STALE] {label} — {why}")

    # ── section coverage (M8-T3): how many of the harness's load-bearing oracle sections have ≥1 mutation ──
    import re as _re_cov
    _all_sections = sorted(set(_re_cov.findall(r"══ (\d+)\.", HARNESS.read_text(encoding="utf-8"))), key=int)
    _mutated_sections = sorted({s.lstrip("§") for *_rest, s in MUTATIONS}, key=int)
    # Sections that are pure spec-presence / arithmetic-skip and need no fixture mutation are documented here
    # (each is exercised by another modality — a property test, a drift guard, or a build-stats recompute):
    _COVERED_BY_OTHER = {
        "2": "toposort — deterministic graph math (mini-typescript), no external oracle to mutate",
        "3": "cost preflight — pure formula", "4": "--lint hash compare", "5": "broken-ref",
        "6": "file→component mapping", "7": "interface-hash propagation", "9": "ORM-drift diff",
        "10": "IF-2 base-type", "11": "IF-5 co-change", "12": "lifecycle diff", "13": "heal floor",
        "14": "FP normalization", "15": "SARIF template (covered by §20/§40)", "16": "dashboard self-containment (covered by §40 G2)",
        "20": "SARIF conformance (covered by §40 G1)",
        "22": "IF-3b contract", "23": "IF-7 swallowed-error", "24": "IF-6 set (covered by §28)",
        "25": "IF-10 in-file (covered by §29/§30)",
        "52": "harness self-test — self-validating (it asserts properties of the suite itself)",
        "53": "public-harness contract — proven live by tools/public_harness.py (run in validate_all + CI)",
        "54": "adversarial renderer/redaction — reuses the §43 viewer + §8 redaction tools (their mutations cover it)",
        "55": "perf/scale sanity — reuses the §35 adapter + §41 exclusion tools (their mutations cover it)",
        "57": "multi-agent projections — the emitter reads the §40 archive; the §17 owned-region + §45 R9 mutations guard its discipline",
        "58": "run-to-run stability — a cross-cutting determinism property of the §35/§41/§43/§50/§36 tools (each already mutation-covered)",
    }
    _uncovered = [s for s in _all_sections if s not in _mutated_sections and s not in _COVERED_BY_OTHER]
    print(f"\n  section coverage: {len(_mutated_sections)}/{len(_all_sections)} harness sections have a direct killing mutation "
          f"({len(_mutated_sections) + len(_COVERED_BY_OTHER)}/{len(_all_sections)} covered incl. cross-modality)")
    print(f"    mutated: §{', §'.join(_mutated_sections)}")
    if _uncovered:
        print(f"    NOT yet covered (review): §{', §'.join(_uncovered)}")
    if survived:
        print("\n  VACUOUS CHECKS DETECTED — the suite did not catch these violations:")
        for label, section in survived:
            print(f"    ✗ {section}: {label}")
    # Each harness subprocess REWRITES validation/_harness_summary.json; a mutation run leaves it in a
    # FAILING state. Re-run the clean (restored) harness once at the very end so the summary the drift
    # guard reads reflects the true all-PASS state, not the last mutation's failure.
    run_harness()

    ok = not survived and not stale
    print(f"\n  RESULT: {'ALL MUTATIONS KILLED — the gated checks are load-bearing' if ok else 'ACTION NEEDED (survived/stale above)'}")
    return 0 if ok else 1


def _result_count(out: str) -> str:
    for line in out.splitlines():
        if "RESULT:" in line:
            return line.split("RESULT:")[1].strip()
    return "?"


def _section_failed(out: str, section: str) -> bool:
    """True iff the harness reported a [FAIL] attributable to `section` (e.g. "§8").

    Most check() names don't embed the §-token, so we ALSO attribute a FAIL to the
    "══ N. …" header that precedes it: track the current header number while scanning,
    and match the section's number (§8 → 8). This confirms the INTENDED check caught the
    mutation rather than collateral damage elsewhere.
    """
    import re as _re
    want = section.lstrip("§").strip()
    cur = None
    for line in out.splitlines():
        m = _re.search(r"══\s*(\d+)\.", line)
        if m:
            cur = m.group(1)
        s = line.strip()
        if s.startswith("[FAIL]"):
            if section in line or cur == want:
                return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
