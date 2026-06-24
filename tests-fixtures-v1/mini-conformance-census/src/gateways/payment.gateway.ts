import { Retryable } from "../core/base";

export class PaymentGateway implements Retryable {
  retry() {
    return true;
  }
  pay(amount: number) {
    return amount;
  }
}
