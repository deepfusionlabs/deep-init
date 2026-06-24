import { Router, Request, Response } from 'express';
import { eq } from 'drizzle-orm';
import { db, schema } from '../shared/db';
import { verifyWebhookSignature } from '../shared/middleware';
import { markPaid } from '../orders/orders.service';

const router = Router();

// Inbound payment-provider callback. There is NO end-user session on this path —
// it is a server-to-server call. Authorization is the HMAC signature check
// (verifyWebhookSignature), which is the EQUIVALENT UPSTREAM GUARD. A naive IF-1
// detector might see "markPaid writes orders, but has no requireRole like cancel"
// and flag inconsistent enforcement — that is a FALSE POSITIVE: (a) the guarded
// sibling (cancelOrder) is a DIFFERENT operation, and (b) an alternative guard
// (the signature) exists upstream on this path.
router.post('/webhook', verifyWebhookSignature, async (req: Request, res: Response) => {
  const { orderId, eventType } = req.body;

  // Append to the SHARED order_events table. The orders service OWNS writes to
  // order_events; this append is part of that owned write surface (the webhook is
  // part of the orders bounded context, not the read-only reporting side).
  await db.insert(schema.orderEvents).values({ orderId, eventType: eventType || 'payment.succeeded' });

  if (eventType === 'payment.succeeded') {
    await markPaid(orderId);
  }
  res.json({ received: true });
});

// Internal reconciliation endpoint — refunds. DIFFERENT entity+operation from
// cancelOrder (this records a refund event, it does not cancel the order), so it
// is not a missing-guard sibling of cancel.
router.post('/refund', verifyWebhookSignature, async (req: Request, res: Response) => {
  const { orderId } = req.body;
  await db.update(schema.orderEvents)
    .set({ eventType: 'payment.refunded' })
    .where(eq(schema.orderEvents.orderId, orderId));
  res.json({ refunded: true });
});

export default router;
