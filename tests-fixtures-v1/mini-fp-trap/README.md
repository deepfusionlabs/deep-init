# mini-fp-trap

Consolidated **false-positive trap** fixture for the DeepInit issue layer.

Every file below is a *legitimate-but-suspicious* pattern: something a naive detector
would flag, but that the issue-layer spec (`skill/references/issues.md`) says MUST be
suppressed. `expected_issues` is empty by design — every pattern is enumerated in
`must_not_fire` with the suppression reason and the spec clause that governs it.

Polyglot-ish billing/orders service:
- `src/` — Node/TypeScript API (orders, payments, webhooks)
- `app/models/` — a Ruby (ActiveRecord) reporting model that shares one table by contract
- `db/migrations/` — the SQL schema the ORM maps to

Each false flag raised against this fixture counts against DeepInit's measured FP rate.
