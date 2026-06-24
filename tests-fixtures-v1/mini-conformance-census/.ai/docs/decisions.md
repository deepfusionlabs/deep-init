<!-- DeepInit | Phase: decisions | Run ID: 2026-06-10T15-00 -->
# Architecture Decision Records

## ADR-100 — Every repository MUST extend BaseRepository

- **Status:** Accepted (2025-08-01)
- **Context:** Repositories share transaction, retry, and audit plumbing that
  lives in `BaseRepository`; a repository that does not extend it silently loses
  the shared connection-pool + audit hooks.
- **Decision:** Every repository class (files matching `src/repos/*.repository.ts`)
  MUST extend `BaseRepository`.
- **Census:** class=`src/repos/*.repository.ts` · conformance=`extends BaseRepository`
- **Provenance:** src/repos/

## ADR-101 — Every service MUST extend LegacyService [DE-FACTO STALE]

- **Status:** Accepted (2024-02-10)
- **Context:** The original service base carried request-scoped DI. The rule was
  never formally superseded, but the platform migrated to `BaseService` (async
  DI) across 2025; only one legacy service still extends `LegacyService`.
- **Decision:** Every service (files matching `src/services/*.service.ts`) MUST
  extend `LegacyService`.
- **Census:** class=`src/services/*.service.ts` · conformance=`extends LegacyService`
- **Provenance:** src/services/

## ADR-102 — The cache layer uses Redis [CARDINALITY-1 — no census]

- **Status:** Accepted (2025-05-01)
- **Context:** A single decision about one component; it does not range over a
  class of sibling sites, so there is no population to take a census over.
- **Decision:** The cache layer uses Redis as its backing store.
- **Provenance:** src/cache/cache.ts

## ADR-103 — Every controller MUST be cohesive [NON-STRUCTURAL property — no census]

- **Status:** Accepted (2025-06-01)
- **Context:** A class-ranging convention, but its required property
  ("cohesive / single-responsibility") has no decidable structural check — no
  AST fact decides conformance, so the census degrades (never guess).
- **Decision:** Every controller (files matching `src/controllers/*.controller.ts`)
  MUST be cohesive and single-responsibility.
- **Provenance:** src/controllers/

## ADR-104 — Every gateway MUST implement Retryable [N<3 — no census]

- **Status:** Accepted (2025-07-01)
- **Context:** A class-ranging convention with a structural check, but the class
  has fewer than 3 members, so no majority can exist — the census degrades.
- **Decision:** Every gateway (files matching `src/gateways/*.gateway.ts`) MUST
  implement `Retryable`.
- **Census:** class=`src/gateways/*.gateway.ts` · conformance=`implements Retryable`
- **Provenance:** src/gateways/
