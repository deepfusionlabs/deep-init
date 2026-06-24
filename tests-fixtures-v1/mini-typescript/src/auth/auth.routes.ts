import { Router, Request, Response } from 'express';
import { registerUser, loginUser, getUserById } from './auth.service';
import { authMiddleware, AuthRequest } from '../shared/middleware';

const router = Router();
router.post('/register', async (req: Request, res: Response) => {
  try { res.status(201).json(await registerUser(req.body)); } catch (e: any) { res.status(400).json({ error: e.message }); }
});
router.post('/login', async (req: Request, res: Response) => {
  try { res.json(await loginUser(req.body.email, req.body.password)); } catch (e: any) { res.status(401).json({ error: e.message }); }
});
router.get('/me', authMiddleware, async (req: AuthRequest, res: Response) => {
  const user = await getUserById(req.userId!);
  user ? res.json(user) : res.status(404).json({ error: 'Not found' });
});
export default router;
