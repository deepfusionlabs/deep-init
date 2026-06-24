import db from '../shared/db';
import { appendAudit } from '../shared/audit-log';

// Orders domain. Owns the `order` table. To fulfil an order it needs to
// decrement available stock — and it does so by writing the `stock` table
// DIRECTLY, rather than calling the inventory domain. There is no inventory
// interface imported here; the only thing the two domains share is the raw
// table. If inventory changes how `reserved`/`onHand` are interpreted, this
// code silently breaks (and vice versa).

export async function placeOrder(userId: string, sku: string, quantity: number) {
  if (quantity <= 0) throw new Error('Quantity must be positive');

  // Direct read of the shared `stock` table (no inventory service call).
  const stock = await db.stock.findUnique({ where: { sku } });
  if (!stock) throw new Error(`Unknown SKU ${sku}`);

  const available = stock.onHand - stock.reserved;
  if (available < quantity) throw new Error('Insufficient stock');

  // Direct write of the shared `stock` table: reserve units. Orders assumes
  // `reserved` is "soft-held, not yet shipped" — inventory has no idea this
  // field is being driven from here.
  await db.stock.update({
    where: { sku },
    data: { reserved: stock.reserved + quantity },
  });

  const order = await db.order.create({
    data: { userId, sku, quantity, status: 'reserved', total: quantity * 100 },
  });

  await appendAudit({
    actor: userId,
    component: 'orders',
    action: 'place',
    detail: `order ${order.id} reserved ${quantity} of ${sku}`,
  });

  return order;
}

// Shipping an order converts a reservation into a real depletion: it both
// drops `reserved` and drops `onHand` on the shared `stock` table — again
// with no coordination with the inventory domain that also owns those fields.
export async function shipOrder(orderId: string) {
  const order = await db.order.findUnique({ where: { id: orderId } });
  if (!order) throw new Error('Order not found');

  const stock = await db.stock.findUnique({ where: { sku: order.sku } });
  if (!stock) throw new Error(`Unknown SKU ${order.sku}`);

  await db.stock.update({
    where: { sku: order.sku },
    data: {
      reserved: stock.reserved - order.quantity,
      onHand: stock.onHand - order.quantity,
    },
  });

  await db.order.update({ where: { id: orderId }, data: { status: 'shipped' } });

  await appendAudit({
    actor: order.userId,
    component: 'orders',
    action: 'ship',
    detail: `order ${order.id} shipped ${order.quantity} of ${order.sku}`,
  });

  return order;
}
