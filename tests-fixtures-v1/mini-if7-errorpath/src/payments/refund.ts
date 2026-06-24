// payments/refund.ts — cross-consumed by gateway, but its catch RE-THROWS, so failures
// propagate to the caller. Must NOT fire (the error is not swallowed).
declare const psp: { refund(id: string): Promise<string> };

export async function refundCard(orderId: string): Promise<string> {
  try {
    return await psp.refund(orderId);
  } catch (e) {
    throw new Error('refund failed: ' + String(e)); // re-raised — propagates, not swallowed
  }
}
