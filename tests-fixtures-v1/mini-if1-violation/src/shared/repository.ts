// In-memory store standing in for the persistence layer.
// All Order rows flow through here; every delete path below ultimately
// reaches deleteOrderRow(), so the *entity + operation* is identical across paths.

export interface Order {
  id: string;
  userId: string;       // the owner
  status: 'open' | 'paid' | 'shipped' | 'cancelled';
  total: number;
  createdAt: string;
}

const ORDERS = new Map<string, Order>();

export function findOrder(id: string): Order | undefined {
  return ORDERS.get(id);
}

export function findOrdersByUser(userId: string): Order[] {
  return [...ORDERS.values()].filter((o) => o.userId === userId);
}

export function listAllOrders(): Order[] {
  return [...ORDERS.values()];
}

// The single low-level delete primitive for the Order entity.
export function deleteOrderRow(id: string): boolean {
  return ORDERS.delete(id);
}

export function saveOrder(order: Order): Order {
  ORDERS.set(order.id, order);
  return order;
}
