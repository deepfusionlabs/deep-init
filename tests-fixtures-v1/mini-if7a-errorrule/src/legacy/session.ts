// Legacy charge retry. ADR-009 (SUPERSEDED) once forbade retry on a gateway
// timeout; current policy (ADR-014 idempotency) sanctions a single keyed retry.
import { chargeCard } from "../payments/gateway";
import { Order } from "../orders/order.repo";

// T8 — SUPERSEDED (must NOT fire): the catch retries the charge on timeout,
// which the SUPERSEDED ADR-009 forbade but current policy explicitly sanctions.
export async function chargeWithRetry(order: Order): Promise<void> {
  try {
    await chargeCard(order.id, order.totalCents);
  } catch (e: any) {
    if (e.code === "timeout") {
      // keyed retry — sanctioned by current policy; ADR-009 is superseded
      await chargeCard(order.id, order.totalCents, { idempotencyKey: order.id });
    } else {
      throw e;
    }
  }
}
