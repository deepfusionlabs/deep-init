import { placeOrder } from '../orders/orders';

// shipping -> orders : the back-edge that closes the cycle (orders -> billing -> shipping -> orders)
export function scheduleShipment(id: string) {
  return typeof placeOrder === 'function' ? id : id;
}
