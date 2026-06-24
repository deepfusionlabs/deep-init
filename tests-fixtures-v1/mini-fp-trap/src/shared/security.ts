import crypto from 'crypto';

export interface JwtClaims { sub: number; role: string; }

// Stub verification helpers. Real impls would use jose / a KMS; the FP-trap only
// needs the call sites to exist so the upstream guards are real.
export function verifyJwt(token: string): JwtClaims | null {
  if (!token) return null;
  try {
    const [, body] = token.split('.');
    const claims = JSON.parse(Buffer.from(body, 'base64url').toString());
    return { sub: claims.sub, role: claims.role };
  } catch {
    return null;
  }
}

export function verifyHmacSignature(body: unknown, signature: string): boolean {
  const secret = process.env.WEBHOOK_SECRET || '';
  const expected = crypto
    .createHmac('sha256', secret)
    .update(JSON.stringify(body))
    .digest('hex');
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
}
