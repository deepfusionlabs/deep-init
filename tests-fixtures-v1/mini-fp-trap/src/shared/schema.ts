// ORM schema definitions (Drizzle-style) mapping the Postgres tables in
// db/migrations/001_init.sql. Types here are chosen to be DIALECT-EQUIVALENT to
// the live schema — see the comments per column. IF-2 must NOT flag drift on
// bare-synonym pairs whose params are identical.

import { pgTable, bigserial, bigint, varchar, boolean, decimal, timestamp, jsonb } from 'drizzle-orm/pg-core';

export const users = pgTable('users', {
  id: bigserial('id', { mode: 'number' }).primaryKey(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  role: varchar('role', { length: 32 }).notNull().default('customer'),
  // DB is `boolean`; ORM `boolean`. Identical base type — no drift.
  isActive: boolean('is_active').notNull().default(true),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
});

export const orders = pgTable('orders', {
  id: bigserial('id', { mode: 'number' }).primaryKey(),
  userId: bigint('user_id', { mode: 'number' }).notNull(),
  // DB column is NUMERIC(12,2); ORM declares decimal(12,2).
  // decimal === numeric (Postgres synonyms) AND precision/scale are identical => NO drift.
  total: decimal('total', { precision: 12, scale: 2 }).notNull(),
  // DB `boolean`; ORM `boolean`. No drift.
  isPaid: boolean('is_paid').notNull().default(false),
  status: varchar('status', { length: 32 }).notNull().default('pending'),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
});

export const orderEvents = pgTable('order_events', {
  id: bigserial('id', { mode: 'number' }).primaryKey(),
  orderId: bigint('order_id', { mode: 'number' }).notNull(),
  eventType: varchar('event_type', { length: 64 }).notNull(),
  payload: jsonb('payload').notNull().default({}),
  occurredAt: timestamp('occurred_at', { withTimezone: true }).notNull().defaultNow(),
});
