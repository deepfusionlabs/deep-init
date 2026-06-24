// payments/charge.ts — the Core money-mutation primitive consumed across the gateway boundary.
declare const psp: { charge(id: string, amount: number): Promise<string> };

export async function chargeCard(orderId: string, amount: number): Promise<string> {
  try {
    return await psp.charge(orderId, amount);
  } catch (e) {
    // BUG (IF-7c): the charge error is swallowed here — a caller in another
    // component (gateway/checkout.ts) cannot see the failure and will mark the
    // order paid as if the charge succeeded.
  }
  return '';
}
