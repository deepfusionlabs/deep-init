// Payment gateway client (stub).
export async function chargeCard(
  orderId: string,
  amountCents: number,
  opts?: { idempotencyKey?: string },
): Promise<void> { void orderId; void amountCents; void opts; }

export const gateway = {
  async refund(orderId: string, amountCents: number): Promise<void> { void orderId; void amountCents; },
};
