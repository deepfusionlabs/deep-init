import { Router, Response } from 'express';
import { placeOrder, getOrdersByUser, getOrder } from './order.service';
import { authMiddleware, AuthRequest } from '../shared/middleware';

const router = Router();
// WF: Place order endpoint — auth required
router.post('/', authMiddleware, async (req: AuthRequest, res: Response) => {
  try { res.status(201).json(await placeOrder(req.userId!, req.body.items)); }
  catch (e: any) { res.status(400).json({ error: e.message }); }
});
router.get('/', authMiddleware, async (req: AuthRequest, res: Response) => {
  res.json(await getOrdersByUser(req.userId!));
});
router.get('/:id', authMiddleware, async (req: AuthRequest, res: Response) => {
  try { res.json(await getOrder(req.params.id, req.userId!)); }
  catch (e: any) { res.status(403).json({ error: e.message }); }
});
export default router;
