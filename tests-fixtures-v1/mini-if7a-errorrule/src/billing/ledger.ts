// Double-entry ledger (stub).
export const ledger = {
  async debit(orderId: string, amountCents: number): Promise<void> { void orderId; void amountCents; },
  async mark(orderId: string, status: string): Promise<void> { void orderId; void status; },
};
