import { PrismaClient } from '@prisma/client';

// Singleton database connection
// Decision: Prisma over TypeORM for type safety and migration tooling
const prisma = new PrismaClient({
  log: process.env.NODE_ENV === 'development' ? ['query'] : [],
});

export default prisma;
