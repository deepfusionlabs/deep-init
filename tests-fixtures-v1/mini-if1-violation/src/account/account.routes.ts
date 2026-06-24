import { Router, Response } from 'express';
import { authMiddleware, AuthRequest } from '../shared/middleware';
import { purgeOwnOrdersOnAccountClose } from '../orders/account.service';

const router = Router();

// Account-closure path — deletes Order rows (same entity + delete operation),
// but the service only ever resolves the CALLER's own orders, so ownership is
// enforced upstream. No per-row owner check is needed here.
router.post('/close', authMiddleware, async (req: AuthRequest, res: Response) => {
  const removed = purgeOwnOrdersOnAccountClose(req.userId!);
  res.json({ closed: true, ordersRemoved: removed });
});

export default router;
