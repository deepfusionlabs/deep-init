import { BaseService } from "../core/base";

export class BillingService extends BaseService {
  charge(amount: number) {
    return this.run("billing.charge", amount);
  }
}
