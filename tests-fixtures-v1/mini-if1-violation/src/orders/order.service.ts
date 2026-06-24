import {
  Order,
  findOrder,
  findOrdersByUser,
  listAllOrders,
  deleteOrderRow,
} from '../shared/repository';

export class OwnershipError extends Error {}
export class NotFoundError extends Error {}

// BR (Core): Only the owner of an order may delete it.
// The canonical ownership check for the Order entity's delete operation.
export function assertOwner(orderId: string, userId: string): Order {
  const order = findOrder(orderId);
  if (!order) {
    throw new NotFoundError(`Order ${orderId} not found`);
  }
  if (order.userId !== userId) {
    throw new OwnershipError('You do not own this order');
  }
  return order;
}

// Single-order delete (web path). Ownership enforced via assertOwner above.
export function deleteOwnedOrder(orderId: string, userId: string): void {
  assertOwner(orderId, userId);
  deleteOrderRow(orderId);
}

// Bulk delete (API/batch path) — reaches the SAME entity + delete operation,
// but loops deleteOrderRow() directly WITHOUT calling assertOwner().
// The ownership rule that deleteOwnedOrder enforces is absent here.
export function bulkDeleteOrders(orderIds: string[]): number {
  let removed = 0;
  for (const id of orderIds) {
    if (deleteOrderRow(id)) {
      removed++;
    }
  }
  return removed;
}

// Cancel is a DIFFERENT operation on the Order entity (status mutation,
// not a delete). It owns its own ownership guard.
export function cancelOwnedOrder(orderId: string, userId: string): Order {
  const order = assertOwner(orderId, userId);
  order.status = 'cancelled';
  return order;
}

export function getOrdersForUser(userId: string): Order[] {
  return findOrdersByUser(userId);
}

// Read-only projection of every order, no per-row mutation.
export function exportAllOrders(): Array<{ id: string; status: string; total: number }> {
  return listAllOrders().map((o) => ({ id: o.id, status: o.status, total: o.total }));
}
