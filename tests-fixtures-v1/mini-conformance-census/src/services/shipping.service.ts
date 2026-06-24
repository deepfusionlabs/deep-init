import { BaseService } from "../core/base";

export class ShippingService extends BaseService {
  ship(orderId: string) {
    return this.run("shipping.ship", orderId);
  }
}
