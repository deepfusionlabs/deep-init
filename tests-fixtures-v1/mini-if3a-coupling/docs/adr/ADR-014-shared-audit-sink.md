# ADR-014: Operational audit is a shared, directly-written sink

- Status: Accepted
- Date: 2025-09-02

## Context

Every domain (orders, inventory, and any future domain) needs to record
operational events for compliance and debugging. We considered routing all
audit writes through an `audit` service, but that would make the audit path a
hard dependency of every domain and a single point of failure.

## Decision

The `audit_log` table is a **sanctioned shared resource**. Any domain MAY
write to it directly via `appendAudit` (see `src/shared/audit-log.ts`).

The table is governed by a strict contract that removes the usual coupling
risk of a shared table:

1. **Append-only.** Rows are only ever inserted — never updated or deleted.
2. **Write-only.** No domain reads `audit_log` for business logic. It feeds
   external compliance tooling only.
3. **Additive schema.** Columns may be added but never repurposed or removed.

Because there is no shared mutable state and no read-back, two domains writing
to `audit_log` cannot break one another. The directness is intentional.

## Consequences

This is a deliberate exception to our "no direct cross-domain table access"
rule. It must NOT be treated as silent coupling: the contract above is what
makes it safe. The `stock` table is explicitly NOT covered by this exception.
