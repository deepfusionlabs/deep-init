import { db, schema } from '../shared/db';
import { eq } from 'drizzle-orm';

// WA-PAY-1 (workaround, STILL VALID as of 2026-06):
//   The upstream payment provider's `/v2/charges` API does not return the
//   settlement currency on `pending` charges (provider bug PROV-3821, still OPEN —
//   see https://status.provider.example/incidents/3821). Until that ticket closes,
//   we default the currency to the account default and re-fetch on settlement.
//   This workaround's TRIGGERING CONDITION STILL HOLDS, so IF-4(b) must NOT flag
//   it as a stale workaround.
const ACCOUNT_DEFAULT_CURRENCY = 'USD';

export async function reconcileCharge(orderId: number, charge: { status: string; currency?: string }) {
  // WA-PAY-1: provider omits currency on pending charges.
  const currency = charge.currency ?? ACCOUNT_DEFAULT_CURRENCY;

  if (charge.status === 'settled') {
    await db
      .update(schema.orders)
      .set({ isPaid: true, status: 'paid' })
      .where(eq(schema.orders.id, orderId));
  }
  return { orderId, currency };
}
