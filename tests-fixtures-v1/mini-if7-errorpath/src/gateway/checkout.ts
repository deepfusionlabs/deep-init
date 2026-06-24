// gateway/checkout.ts — the downstream that ASSUMES chargeCard raises on failure, then
// marks the order paid. Imports several payments primitives across the component boundary.
import { chargeCard } from '../payments/charge';
import { refundCard } from '../payments/refund';
import { getRateWithFallback } from '../payments/rates';
import { recordAudit } from '../payments/audit';
import { withSession } from '../payments/session';

export async function checkout(orderId: string, amount: number): Promise<string> {
  const rate = getRateWithFallback('USD');
  await withSession(orderId);
  const ref = await chargeCard(orderId, amount * rate); // assumes this throws if the charge fails
  markOrderPaid(orderId, ref);                          // ...so reaching here is treated as success
  recordAudit(orderId, ref);
  return ref;
}

export async function undo(orderId: string): Promise<string> {
  return refundCard(orderId);
}

function markOrderPaid(orderId: string, ref: string): void {
  /* persists order.paid = true, ref */
}
