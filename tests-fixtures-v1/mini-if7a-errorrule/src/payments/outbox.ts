// Transactional outbox writer.
// Governed by ADR-021 (.ai/docs/decisions.md): "A failed outbox write MUST abort
// the transaction (event not published)" — the catch MUST NOT commit.
import { Tx } from "../orders/order.repo";

interface Event { id: string; type: string; payload: unknown }

// E3 — IF-7(a) COMMISSION (MUST fire): on a failed outbox write the catch logs
// and then commits the transaction anyway — treating a failed publish as
// success, the exact effect ADR-021 forbids on the error path.
export async function publishEvent(tx: Tx, ev: Event): Promise<void> {
  try {
    await tx.insert("outbox", ev);
    await tx.commit();
  } catch (e) {
    console.error("outbox write failed", e);
    // commit anyway — VIOLATES ADR-021 (must abort the transaction)
    await tx.commit();
  }
}
