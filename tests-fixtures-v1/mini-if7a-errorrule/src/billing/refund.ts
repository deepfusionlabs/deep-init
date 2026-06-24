// Refund processing.
import { ledger } from "./ledger";
import { gateway } from "../payments/gateway";

// T4 — SOFT RULE (must NOT fire): only an advisory comment ("should probably"),
// not a hard documented invariant; the catch does not roll back.
export async function refund(orderId: string, amountCents: number): Promise<void> {
  await ledger.debit(orderId, amountCents);
  try {
    await gateway.refund(orderId, amountCents);
  } catch (e) {
    // we should probably roll back the ledger entry here eventually (TODO)
    console.error("refund failed", e);
  }
}

// T7 — ONE-SIDED / NO DOCUMENTED RULE (must NOT fire): the catch sets a status
// that may look wrong, but NO documented rule governs this error behaviour, so
// there is nothing to dual-cite (one-sided → drop).
export async function refundWithStatus(orderId: string): Promise<void> {
  try {
    await gateway.refund(orderId, 0);
  } catch (e) {
    await ledger.mark(orderId, "refund_attempted");
  }
}
