import { login } from '../auth/login';
// BR: Invoice amount must be positive
export function createInvoice(userId: string, amount: number) {
  if (amount <= 0) throw new Error('Amount must be positive');
  return { invoiceId: 'inv-001', amount };
}
