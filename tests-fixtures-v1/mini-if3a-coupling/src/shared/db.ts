import { PrismaClient } from '@prisma/client';

// Singleton Prisma client. Components import this directly and issue
// their own queries — there is intentionally no repository/service layer
// wrapping table access, so coupling through a shared table is invisible
// at the import graph level.
const db = new PrismaClient({
  log: process.env.NODE_ENV === 'development' ? ['query'] : [],
});

export default db;
