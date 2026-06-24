import { Router, Response } from 'express';
import { placeOrder, cancelOrder, markPaid } from './orders.service';
import { authMiddleware, requireRole, AuthRequest } from '../shared/middleware';

const router = Router();

// PLACE order — owner-only enforced upstream: authMiddleware attaches req.userId,
// and we always insert with THAT id. No way to write another user's order here.
router.post('/', authMiddleware, async (req: AuthRequest, res: Response) => {
  const order = await placeOrder({ userId: req.userId!, total: req.body.total });
  res.status(201).json(order);
});

// CANCEL order — GUARDED admin write. This is the role-guarded sibling that the
// webhook markPaid path (DIFFERENT entity/operation) is contrasted against. The
// contrast is NOT exact: cancel != markPaid, so IF-1(a) must not pair them.
router.post('/:id/cancel', authMiddleware, requireRole('admin'), async (req: AuthRequest, res: Response) => {
  res.json(await cancelOrder(Number(req.params.id)));
});

export default router;
