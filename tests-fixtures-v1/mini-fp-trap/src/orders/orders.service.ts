import { eq } from 'drizzle-orm';
import { db, schema } from '../shared/db';

// BR-ORD-1: Only an admin may CANCEL an order (refund-bearing operation).
// BR-ORD-2: The order total must be >= 0.
// BR-ORD-3: A user may PLACE an order for themselves only.

export interface NewOrder { userId: number; total: string; }

// Self-service write: PLACE order. Authorization that the caller is the owner is
// enforced UPSTREAM at the router (authMiddleware sets req.userId, and the route
// passes that same userId in — there is no cross-user write surface here).
export async function placeOrder(input: NewOrder) {
  if (Number(input.total) < 0) throw new Error('total must be non-negative');
  const [row] = await db
    .insert(schema.orders)
    .values({ userId: input.userId, total: input.total, status: 'pending' })
    .returning();
  return row;
}

// Admin write: CANCEL order. This is the GUARDED sibling for entity=order,
// operation=cancel. The role guard lives on the route (requireRole('admin')).
export async function cancelOrder(orderId: number) {
  const [row] = await db
    .update(schema.orders)
    .set({ status: 'cancelled' })
    .where(eq(schema.orders.id, orderId))
    .returning();
  return row;
}

export async function markPaid(orderId: number) {
  const [row] = await db
    .update(schema.orders)
    .set({ isPaid: true, status: 'paid' })
    .where(eq(schema.orders.id, orderId))
    .returning();
  return row;
}
