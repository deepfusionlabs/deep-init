export const meta = {
  name: 'init-vs-deepinit-scoring',
  description: 'Blind independent verifiers score each captured /init and DeepInit CLAUDE.md against the real cloned code',
  phases: [{ title: 'Score', detail: 'one independent code-grounded verifier per captured output' }],
}

const SCORECARD = {
  type: 'object', additionalProperties: false,
  properties: {
    claims_total: { type: 'integer' },
    claims_grounded: { type: 'integer' },
    grounding_pct: { type: 'number' },
    claims_checked: { type: 'integer' },
    claims_refuted: { type: 'integer' },
    faithfulness_pct: { type: 'number' },
    depth_by_kind: {
      type: 'array',
      items: { type: 'object', additionalProperties: false,
               properties: { kind: { type: 'string' }, count: { type: 'integer' } },
               required: ['kind', 'count'] },
    },
    issues_flagged: { type: 'integer' },
    issues_real: { type: 'integer' },
    issues_fabricated: { type: 'integer' },
    wrong_high: { type: 'integer' },
    dep_edge_recall_pct: { type: ['number', 'null'] },
    actionability_1to5: { type: 'integer' },
    notes: { type: 'string' },
  },
  required: ['claims_total', 'claims_grounded', 'grounding_pct', 'claims_checked', 'claims_refuted',
             'faithfulness_pct', 'depth_by_kind', 'issues_flagged', 'issues_real', 'issues_fabricated',
             'wrong_high', 'dep_edge_recall_pct', 'actionability_1to5', 'notes'],
}

function scorePrompt(t) {
  return `You are an INDEPENDENT, skeptical code-grounding verifier. You did NOT write the file under review (separation of duties). Score it by the rubric below — apply the SAME objective standard no matter the writing style or which tool may have produced it.

REPOSITORY: ${t.repo}  (${t.lang}, ${t.tier}-tier, ${t.fame})
SOURCE CODE (read-only, the ground truth): ${t.clone}
  → Use Read / Grep / LS on this path to verify every claim against the ACTUAL files and line numbers.

THE CANDIDATE CONTEXT FILE TO SCORE: ${t.candidate_path}
  → Read it first. It is one "agent context" file (a CLAUDE.md) meant to brief a coding agent on this repo.

RUBRIC — work claim-by-claim, opening real files to verify:
1. claims_total — split the file into discrete, checkable factual claims about the code (architecture, components, roles, dependencies/imports, key invariants, data stores, boundary/business rules, technology choices, build/test commands, conventions). Skip pure boilerplate ("This file provides guidance to Claude Code…").
2. claims_grounded / grounding_pct — a claim is GROUNDED only if it carries a VERIFIABLE \`file:line\` citation: a specific file AND a line number (or line range) that you OPEN and confirm actually supports the claim. A bare filename, a symbol name, or a file with no line number is NOT grounded even if it exists. Spot-open citations to confirm they resolve. grounding_pct = 100*claims_grounded/claims_total.
3. claims_checked / claims_refuted / faithfulness_pct — for every claim you can locate the relevant code for (cited or not), decide if it is CODE-REFUTED (contradicted by the real code). faithfulness_pct = 100*(claims_checked-claims_refuted)/claims_checked.
4. depth_by_kind — bucket each claim by fact-kind, returning a list of {kind,count}. Use these kinds: component-exists, component-role, entry-point, dependency-edge, technology-choice, data-store, boundary-rule, key-invariant, command-build, style-convention, other.
5. issues_flagged / issues_real / issues_fabricated — count problems/risks/bugs the file calls out; verify each against the code (real vs fabricated).
6. wrong_high — count claims asserted as definite/HIGH-confidence fact that are CODE-REFUTED (the cardinal trust violation).
7. dep_edge_recall_pct — ${t.oracle
      ? `an AST dependency-edge oracle is at ${t.oracle} (read it). Extract the dependency/import relationships the candidate asserts, match them at the component-pair level to the oracle's internal_import_edges, and compute 100*matched/internal_edge_count.`
      : `no oracle for this repo — set dep_edge_recall_pct = null.`}
8. actionability_1to5 — your holistic judgment (1=useless, 5=excellent) of how much this file would actually help a coding agent make a correct change in THIS repo WITHOUT re-reading everything: rewards verifiable, non-obvious, change-relevant facts; penalizes vague/ungrounded/obvious filler.

In notes: give file:line evidence for ~3 grounded claims, EVERY refuted claim, and one line on the file's biggest strength + biggest weakness. Be rigorous and fair — actually open files in ${t.clone}.

Return the scorecard.`
}

let _a = args
if (typeof _a === 'string') { try { _a = JSON.parse(_a) } catch (e) { _a = [] } }
const tasks = Array.isArray(_a) ? _a : ((_a && _a.tasks) || [])
log(`scoring ${tasks.length} captured outputs against real cloned code …`)

const results = await parallel(tasks.map(t => () =>
  agent(scorePrompt(t), { label: `score:${t.label}`, phase: 'Score', schema: SCORECARD })
    .then(sc => sc ? { key: t.key, label: t.label, repo: t.repo, lang: t.lang, tier: t.tier, fame: t.fame, ...sc } : null)
))

const ok = results.filter(Boolean)
log(`scored ${ok.length}/${tasks.length} (failed/skipped: ${tasks.length - ok.length})`)
return ok
