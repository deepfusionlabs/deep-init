import { createInvoice } from '../billing/billing';

// orders -> billing (closes part of the orders->billing->shipping->orders cycle)
export function placeOrder(id: string) {
  return createInvoice(id);
}
