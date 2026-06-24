import db from '../shared/db';
import { appendAudit } from '../shared/audit-log';

// Inventory domain. Owns the `stock` table conceptually: receiving goods,
// stock-takes, and answering "how many on hand" all live here.

// Record a goods receipt: increase on-hand for a SKU.
export async function receiveStock(sku: string, units: number, operator: string) {
  if (units <= 0) throw new Error('Receipt must be a positive quantity');

  // Direct read/write of the shared `stock` table.
  const row = await db.stock.findUnique({ where: { sku } });
  if (!row) {
    await db.stock.create({ data: { sku, onHand: units, reserved: 0 } });
  } else {
    await db.stock.update({
      where: { sku },
      data: { onHand: row.onHand + units },
    });
  }

  // Sanctioned shared sink — write-only, see ADR-014.
  await appendAudit({
    actor: operator,
    component: 'inventory',
    action: 'receive',
    detail: `${units} units of ${sku}`,
  });
}

// Stock-take correction: set on-hand to a counted absolute value.
export async function reconcileStock(sku: string, countedOnHand: number, operator: string) {
  await db.stock.update({
    where: { sku },
    data: { onHand: countedOnHand },
  });

  await appendAudit({
    actor: operator,
    component: 'inventory',
    action: 'reconcile',
    detail: `${sku} set to ${countedOnHand}`,
  });
}

export async function getOnHand(sku: string): Promise<number> {
  const row = await db.stock.findUnique({ where: { sku } });
  return row ? row.onHand - row.reserved : 0;
}
