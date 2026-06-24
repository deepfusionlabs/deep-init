import { placeOrder, shipOrder } from './orders.service';

// Thin HTTP layer for the orders domain. Delegates to the service;
// no table access here.
export const ordersRoutes = {
  'POST /orders': async (body: { userId: string; sku: string; quantity: number }) => {
    const order = await placeOrder(body.userId, body.sku, body.quantity);
    return { id: order.id, status: order.status };
  },
  'POST /orders/:id/ship': async (params: { id: string }) => {
    const order = await shipOrder(params.id);
    return { id: order.id, status: order.status };
  },
};
