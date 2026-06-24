import { Request, Response, NextFunction } from 'express';
import { verifyJwt, verifyHmacSignature } from './security';

export interface AuthRequest extends Request {
  userId?: number;
  userRole?: string;
}

// Standard user auth: validates the JWT and attaches userId/role.
export function authMiddleware(req: AuthRequest, res: Response, next: NextFunction) {
  const token = (req.headers.authorization || '').replace(/^Bearer /, '');
  const claims = verifyJwt(token);
  if (!claims) return res.status(401).json({ error: 'unauthenticated' });
  req.userId = claims.sub;
  req.userRole = claims.role;
  next();
}

// Role gate. Used to protect admin-only write paths.
export function requireRole(role: string) {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (req.userRole !== role) return res.status(403).json({ error: 'forbidden' });
    next();
  };
}

// Webhook auth: there is NO user JWT on an inbound provider callback. Instead the
// payment provider signs the body with a shared secret; we verify the HMAC.
// This is an EQUIVALENT UPSTREAM GUARD for the webhook write path — a different
// authorization mechanism, not a missing one.
export function verifyWebhookSignature(req: Request, res: Response, next: NextFunction) {
  const sig = req.headers['x-provider-signature'] as string | undefined;
  if (!sig || !verifyHmacSignature(req.body, sig)) {
    return res.status(401).json({ error: 'invalid signature' });
  }
  next();
}
