// Payment charge + fulfilment.
// Governed by ADR-014 (.ai/docs/decisions.md): "On payment failure the order
// MUST NOT be marked paid" — except on an idempotency replay.
import { chargeCard } from "./gateway";
import { Order, save } from "../orders/order.repo";

// E1 — IF-7(a) COMMISSION (MUST fire): the catch marks the order paid on a
// charge failure, the exact effect ADR-014 forbids on the error path.
export async function chargeAndFulfill(order: Order): Promise<void> {
  try {
    await chargeCard(order.id, order.totalCents);
  } catch (e) {
    // proceed as if the charge succeeded — VIOLATES ADR-014
    order.status = "paid";
    await save(order);
  }
}

// T1 — DOCUMENTED-EXCEPTION (must NOT fire): marks paid ONLY in the
// idempotency-replay branch, which ADR-014 explicitly sanctions.
export async function chargeWithIdempotency(order: Order): Promise<void> {
  try {
    await chargeCard(order.id, order.totalCents);
  } catch (e: any) {
    if (e.code === "idempotency_replay") {
      // prior charge already succeeded — ADR-014's sanctioned exception
      order.status = "paid";
      await save(order);
    } else {
      throw e;
    }
  }
}

// T6 — RECONCILED (must NOT fire): the catch optimistically sets paid, but a
// finally resets it before return whenever the charge did not actually succeed.
export async function chargeWithGuard(order: Order): Promise<void> {
  let charged = false;
  try {
    await chargeCard(order.id, order.totalCents);
    charged = true;
    order.status = "paid";
  } catch (e) {
    order.status = "paid";
  } finally {
    if (!charged) {
      order.status = "pending";
      await save(order);
    }
  }
}
