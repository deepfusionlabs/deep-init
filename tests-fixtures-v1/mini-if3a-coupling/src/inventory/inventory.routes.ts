import { receiveStock, reconcileStock, getOnHand } from './inventory.service';

// Thin HTTP layer for the inventory domain. Delegates to the service;
// no table access here.
export const inventoryRoutes = {
  'POST /inventory/receive': async (body: { sku: string; units: number; operator: string }) => {
    await receiveStock(body.sku, body.units, body.operator);
    return { ok: true };
  },
  'POST /inventory/reconcile': async (body: { sku: string; onHand: number; operator: string }) => {
    await reconcileStock(body.sku, body.onHand, body.operator);
    return { ok: true };
  },
  'GET /inventory/:sku/on-hand': async (params: { sku: string }) => {
    return { sku: params.sku, onHand: await getOnHand(params.sku) };
  },
};
