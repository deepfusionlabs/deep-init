-- Postgres schema for the billing/orders service.
-- This is the live schema that the TypeScript ORM (src/shared/schema.ts) and the
-- Ruby reporting model (app/models/order_report.rb) both map to.

CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    role          VARCHAR(32)  NOT NULL DEFAULT 'customer',
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT       NOT NULL REFERENCES users(id),
    -- money column: declared NUMERIC here, mapped as `decimal(12,2)` in the ORM.
    -- decimal and numeric are exact synonyms in Postgres; params (12,2) match the ORM.
    total         NUMERIC(12,2) NOT NULL,
    -- boolean stored the dialect-portable way; ORM maps it as `boolean`.
    is_paid       BOOLEAN      NOT NULL DEFAULT FALSE,
    status        VARCHAR(32)  NOT NULL DEFAULT 'pending',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- SHARED TABLE (IF-3a contract). The orders service OWNS writes to order_events.
-- The reporting model is READ-ONLY against it. Contract documented in
-- docs/shared-tables.md (ADR-014) and enforced by the DB role `reporting_ro`.
CREATE TABLE order_events (
    id            BIGSERIAL PRIMARY KEY,
    order_id      BIGINT       NOT NULL REFERENCES orders(id),
    event_type    VARCHAR(64)  NOT NULL,
    payload       JSONB        NOT NULL DEFAULT '{}',
    occurred_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_order_events_order_id ON order_events(order_id);
