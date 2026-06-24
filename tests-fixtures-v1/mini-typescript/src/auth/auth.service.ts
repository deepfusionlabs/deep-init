import bcrypt from 'bcrypt';
import prisma from '../shared/database';
import { generateToken } from '../shared/middleware';
import { logger } from '../shared/logger';

const BCRYPT_ROUNDS = 12;
const MIN_PASSWORD_LENGTH = 8;

// BR: Email must be unique across all users
// BR: Password minimum 8 characters
// BR: Password hashed with bcrypt (12 rounds)
export async function registerUser(input: { email: string; password: string; name: string }) {
  if (input.password.length < MIN_PASSWORD_LENGTH) throw new Error('Password too short');
  const existing = await prisma.user.findUnique({ where: { email: input.email } });
  if (existing) throw new Error('Email already registered');
  const hashed = await bcrypt.hash(input.password, BCRYPT_ROUNDS);
  const user = await prisma.user.create({
    data: { email: input.email, password: hashed, name: input.name, role: 'customer' },
  });
  logger.info('User registered', { userId: user.id });
  return { user: { id: user.id, email: user.email, name: user.name }, token: generateToken(user.id, user.role) };
}

// WF: Login — find by email → verify password → generate JWT
export async function loginUser(email: string, password: string) {
  const user = await prisma.user.findUnique({ where: { email } });
  if (!user) throw new Error('Invalid credentials');
  if (!(await bcrypt.compare(password, user.password))) throw new Error('Invalid credentials');
  return { user: { id: user.id, email: user.email, name: user.name }, token: generateToken(user.id, user.role) };
}

export async function getUserById(id: string) {
  return prisma.user.findUnique({ where: { id }, select: { id: true, email: true, name: true, role: true } });
}
