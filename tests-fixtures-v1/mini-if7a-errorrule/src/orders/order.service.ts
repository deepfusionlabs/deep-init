// Order placement. ADR-007: confirmation notifications MUST be enqueued, never
// sent inline on the success path.
import { sendEmail } from "../notify/sender";
import { Order } from "./order.repo";

// T2 — IF-4 HAPPY-PATH (must route to IF-4, NOT IF-7(a)): the contradiction of
// ADR-007 is on the SUCCESS path (an inline send), not inside any error handler.
export async function placeOrder(order: Order): Promise<void> {
  order.status = "placed";
  // VIOLATES ADR-007 — inline send on the happy path (this is IF-4, not IF-7a)
  await sendEmail(order.customerEmail, "Order confirmed");
}
