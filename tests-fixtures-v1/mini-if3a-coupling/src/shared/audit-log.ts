import db from './db';

// ----------------------------------------------------------------------------
// SANCTIONED SHARED RESOURCE — see ADR-014 "Operational audit is a shared sink".
//
// CONTRACT (intentional, reviewed): every domain MAY write to `audit_log`
// directly. It is an append-only, write-only sink — no domain ever reads it
// back for business logic, no row is ever updated or deleted, and the schema
// is frozen (additive-only). Because there is no read-back and no mutation,
// two domains writing here cannot break each other: there is no shared state
// to drift. This is a DELIBERATE exception to the "no direct cross-domain
// table access" rule, documented here so it is not mistaken for silent
// coupling. Do not introduce a service in front of it; the directness is the
// point (every domain can audit without taking a dependency on another).
// ----------------------------------------------------------------------------

export interface AuditEntry {
  actor: string;
  component: string;
  action: string;
  detail: string;
}

// Single, append-only write helper. The only operation any domain performs
// against `audit_log`.
export async function appendAudit(entry: AuditEntry): Promise<void> {
  await db.auditLog.create({
    data: {
      actor: entry.actor,
      component: entry.component,
      action: entry.action,
      detail: entry.detail,
    },
  });
}
