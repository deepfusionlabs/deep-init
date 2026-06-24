import { Router, Response } from 'express';
import { authMiddleware, AuthRequest } from '../shared/middleware';
import {
  deleteOwnedOrder,
  bulkDeleteOrders,
  cancelOwnedOrder,
  getOrdersForUser,
  exportAllOrders,
  OwnershipError,
  NotFoundError,
} from './order.service';

const router = Router();

router.get('/', authMiddleware, async (req: AuthRequest, res: Response) => {
  res.json(getOrdersForUser(req.userId!));
});

// Web path — delete a single order. Owner-only delete is enforced:
// deleteOwnedOrder() calls assertOwner() before deleting the row.
router.delete('/:id', authMiddleware, async (req: AuthRequest, res: Response) => {
  try {
    deleteOwnedOrder(req.params.id, req.userId!);
    res.status(204).end();
  } catch (e) {
    if (e instanceof OwnershipError) return res.status(403).json({ error: e.message });
    if (e instanceof NotFoundError) return res.status(404).json({ error: e.message });
    res.status(400).json({ error: 'delete failed' });
  }
});

// Bulk/API path — delete MANY orders. SAME entity (Order) + SAME operation
// (delete) as the single-delete route above, but it hands the raw id list
// straight to bulkDeleteOrders(), which never checks ownership. The owner-only
// rule enforced on DELETE /:id is ABSENT on this sibling path.
router.post('/bulk-delete', authMiddleware, async (req: AuthRequest, res: Response) => {
  const ids: string[] = req.body.orderIds ?? [];
  const removed = bulkDeleteOrders(ids);
  res.json({ removed });
});

// Cancel — a DIFFERENT operation (status change, not delete). Owner-guarded.
router.post('/:id/cancel', authMiddleware, async (req: AuthRequest, res: Response) => {
  try {
    res.json(cancelOwnedOrder(req.params.id, req.userId!));
  } catch (e) {
    if (e instanceof OwnershipError) return res.status(403).json({ error: e.message });
    res.status(404).json({ error: 'not found' });
  }
});

// Read-only export — touches the Order entity but performs NO write/delete.
// A different operation (read) from the owner-only delete rule.
router.get('/export', authMiddleware, async (_req: AuthRequest, res: Response) => {
  res.json(exportAllOrders());
});

export default router;
