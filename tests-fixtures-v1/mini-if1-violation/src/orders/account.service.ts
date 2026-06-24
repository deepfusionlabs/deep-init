import { findOrdersByUser, deleteOrderRow } from '../shared/repository';

// Account-closure path. This ALSO deletes Order rows (same entity + delete
// operation as bulkDeleteOrders / deleteOwnedOrder), BUT it scopes the set to
// the caller's own orders via findOrdersByUser(userId) — an equivalent upstream
// ownership guard. Every row it touches is, by construction, owned by userId,
// so no per-row assertOwner is needed.
export function purgeOwnOrdersOnAccountClose(userId: string): number {
  const own = findOrdersByUser(userId); // upstream ownership filter
  let removed = 0;
  for (const order of own) {
    deleteOrderRow(order.id);
    removed++;
  }
  return removed;
}
