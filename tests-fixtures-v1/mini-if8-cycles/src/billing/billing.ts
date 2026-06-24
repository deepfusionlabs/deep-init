import { scheduleShipment } from '../shipping/shipping';

// billing -> shipping
export function createInvoice(id: string) {
  return scheduleShipment(id);
}
