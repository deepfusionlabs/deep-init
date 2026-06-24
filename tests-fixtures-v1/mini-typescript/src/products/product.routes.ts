import { Router, Request, Response } from 'express';
import { createProduct, listProducts, getProduct, adjustStock } from './product.service';
import { authMiddleware, adminOnly, AuthRequest } from '../shared/middleware';

const router = Router();
router.get('/', async (req: Request, res: Response) => {
  const page = parseInt(req.query.page as string) || 1;
  res.json(await listProducts(page));
});
router.get('/:id', async (req: Request, res: Response) => {
  const product = await getProduct(req.params.id);
  product ? res.json(product) : res.status(404).json({ error: 'Not found' });
});
// BR: Only admin can create products
router.post('/', authMiddleware, adminOnly, async (req: Request, res: Response) => {
  try { res.status(201).json(await createProduct(req.body)); } catch (e: any) { res.status(400).json({ error: e.message }); }
});
// BR: Only admin can adjust stock
router.patch('/:id/stock', authMiddleware, adminOnly, async (req: Request, res: Response) => {
  try { res.json(await adjustStock(req.params.id, req.body.quantity)); } catch (e: any) { res.status(400).json({ error: e.message }); }
});
export default router;
