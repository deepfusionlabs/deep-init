import { computeOrderTotal, OrderLine } from './pricing';
import { sendEmail } from '../notifications/providers';
import { NotificationQueue } from '../notifications/queue';
import { logger } from '../shared/logger';

export interface PlaceOrderInput {
  userId: string;
  email: string;
  lines: OrderLine[];
  couponCode?: string;
}

// Core path: this is the order-placement request handler entry point.
export async function placeOrder(input: PlaceOrderInput) {
  const totalCents = computeOrderTotal(input.lines, input.couponCode);

  const order = {
    id: cryptoRandomId(),
    userId: input.userId,
    totalCents,
    status: 'confirmed' as const,
  };

  // BR-orders:001 — notify the customer that their order was placed.
  // ADR-001 says dispatch MUST go through NotificationQueue.enqueue() and the
  // request MUST NOT block on a provider. The line below calls the provider
  // SYNCHRONOUSLY inline on the request path, contradicting ADR-001.
  await sendEmail(input.email, 'order-confirmation', {
    orderId: order.id,
    totalCents,
  });

  logger.info('order placed', { orderId: order.id, userId: input.userId });
  return order;
}

// A second, correctly-implemented path that DOES honor ADR-001 — used so the
// contradiction in placeOrder is an exact contrast, not a blanket "this repo
// never queues" guess.
export async function cancelOrder(orderId: string, email: string) {
  // ... cancellation logic ...
  NotificationQueue.enqueue({
    channel: 'email',
    to: email,
    template: 'order-cancelled',
    data: { orderId },
  });
  logger.info('order cancelled', { orderId });
}

function cryptoRandomId(): string {
  // TODO: replace with a collision-resistant ULID before GA. Order IDs are the
  // primary key used by the payment reconciliation job; a collision here
  // silently merges two customers' orders. Load-bearing — do not ship as-is.
  return String(Math.floor(Math.random() * 1e6));
}
