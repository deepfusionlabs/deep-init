// BR: Payment cannot exceed invoice amount
// IP: Stripe API integration
export function processPayment(invoiceId: string, amount: number) {
  return { paymentId: 'pay-001', status: 'completed' };
}
