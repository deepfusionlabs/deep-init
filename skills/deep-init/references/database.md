# database.md — C3-DB (live schema + ORM-drift)

Analyzes any database Claude Code can reach via MCP or CLI. **Read global-rules §R7 (DB security) and `redaction.md` (PII) before any query.** Skipped cleanly if `--skip-db` or no DB detected.

## Gate (global-rules §R7, mandatory)
Show the masked connection string → require explicit `y/n` → REFUSE strings containing `prod`/`production`/`master` or a known production host (e.g. `*.rds.amazonaws.com`, `*.database.azure.com`, `*.cloudsql.*` — non-exhaustive; see §R7) → READ-ONLY only (`SELECT`/`information_schema`; never write) → prefer MCP over CLI.

## The plain-language DB card (the R10 face of the gate)
What the USER sees is plain — never DeepInit's internal vocabulary. When a DB is detected, the *database card* of the consolidated run-start prompt (`SKILL.md` *Run-start prompt*) asks, in plain words:

> *"I found a database — read it live to check the real schema? (Read-only; I never touch production.)"*  → **No — use the code only** *(recommended)* · **Yes, read it**

When **several environments** are configured (dev / staging / prod — common), it first shows a plain **environment picker** built from the detected configs (e.g. *Dev (app_dev)* · *Staging (app_stage)* · *Prod (…)* · *Don't read any database*). A **production / managed-cloud** host is shown but **auto-declined to code-only** (`db_gate.classify_host == 'refuse'`) — never offered as a live target. The recommendation is the conservative **code-only** (a false-connect is the trust-killer). The deterministic option logic is `tools/db_gate.py` `db_prompt_options()` (it reuses `classify_host`, so the picker and the hard gate can't diverge); harness §97 pins it.

It must **NEVER** leak the internal terms the improvised prompt did — *"Database analysis for ORM-drift (IF-2)?"*, *"the R7 gate"*, *"live-drift"*, *"information_schema"*, *"EF migrations"*, *"NPoco"* (**R10**). Those names live here and in the issue ledger, never on a button. Choosing a live read then runs the mandatory **§R7** sequence above unchanged (mask → y/n → refuse-prod → read-only). Choosing code-only derives the schema from migrations / ORM models / SQL scripts and **suppresses the IF-2 live-drift checks** (no false drift from one side).

## Detection priority
MCP DB tool → CLI (`psql`, `mysql`, `sqlite3`, `sqlcmd`, `mongosh`, `redis-cli`, `neo4j` cypher, `curl` for HTTP APIs) → neither (skip, note in `discovery.md`).

## Analysis principles (apply to ANY DB; skip what doesn't apply)
1. Structure discovery (tables/collections/keyspaces/indexes). 2. Schema extraction (fields/types/constraints/relationships, explicit or inferred). 3. Volume assessment (counts/size/growth). 4. Data sampling (representative records, **PII-obfuscated**). 5. Quality indicators (orphans, type inconsistency, missing required). 6. Business logic in DB (stored procs, triggers, functions, TTLs). 7. Access patterns (indexes, hot fields, slow-query indicators).

## Reference queries (SQL — the operational lift)
**Tables & columns:**
```sql
-- PostgreSQL
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name, ordinal_position;
-- MySQL/MariaDB: same, WHERE table_schema=DATABASE()
-- SQL Server: INFORMATION_SCHEMA.COLUMNS, WHERE TABLE_SCHEMA='dbo'
-- SQLite: SELECT name FROM sqlite_master WHERE type='table'; then PRAGMA table_info({t});
-- Oracle: all_tab_columns WHERE owner=USER
```
**Primary/foreign keys:** `information_schema.table_constraints` + `key_column_usage` + `constraint_column_usage` (PG); `KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_NAME IS NOT NULL` (MySQL); `sys.foreign_keys` (SQL Server); `PRAGMA foreign_key_list({t})` (SQLite).
**Indexes:** `pg_indexes` (PG); `information_schema.STATISTICS` (MySQL); `sys.indexes`+`index_columns` (SQL Server); `sqlite_master WHERE type='index'`.
**Stored procs / functions / triggers / views:** `information_schema.routines`/`triggers`/`views` (PG/MySQL); `sys.objects` + `sys.sql_modules` (SQL Server); `sqlite_master WHERE type IN ('view','trigger')` (SQLite has no procs).
**Volume:** `pg_stat_user_tables.n_live_tup` (PG); `information_schema.TABLES.TABLE_ROWS` (MySQL); `sys.partitions` (SQL Server); `COUNT(*)` per table (SQLite).
**Column stats:** `COUNT(*)`, `COUNT(DISTINCT col)`, null count, MIN/MAX per column.
**Sample records:** 3–5 representative rows, `LIMIT`/`TOP`/`FETCH FIRST` per dialect — **PII obfuscation mandatory** (`redaction.md`).

## Non-SQL (stubs — full set lifted from v1)
- **MongoDB:** `db.getCollectionNames()`; infer schema via `$sample` aggregation (field presence: >90% required / >50% common / <50% optional); `$lookup` + `_id`-suffixed fields → relationships; `getIndexes()`; change streams / Atlas triggers → event logic.
- **Redis/KV:** `INFO keyspace`/`memory`, `DBSIZE`; sample key patterns (`--scan --pattern` → prefix tree); TYPE/TTL/MEMORY USAGE distribution; pub/sub channels; Lua scripts. Output a key-pattern taxonomy as the de-facto schema.
- **Neo4j/graph:** node labels + counts (`MATCH (n) RETURN labels(n), count(*)`); relationship types; properties per label; `SHOW CONSTRAINTS`/`SHOW INDEXES`.
- **Elasticsearch/OpenSearch:** `_cat/indices`; `{index}/_mapping`; `_count`; sample docs (PII-obfuscated).
- **Unknown DB:** identify the query interface and run the 7 analysis principles with whatever's available; document type/version/access method + what couldn't be analyzed.

General: detect type FIRST then adapt; failed query → log + try alternatives; managed DBs may restrict system views; multiple DBs per project are common (analyze each separately).

## ORM-drift diff (v2)
*Refines v1's data-layer Schema Drift Report by doing it at field/type granularity.* After reading the live schema AND documenting the ORM model (from `extraction.md` §5 Data Models), **reconcile the two and report drift** — this is a non-obviousness-perfect finding (inferable from neither half alone):

```markdown
| Entity (ORM) | Table (live) | Field | ORM says | DB says | Drift | Severity |
|--------------|-------------|-------|----------|---------|-------|----------|
| Invoice | invoices | total | decimal(10,2) | numeric(12,4) | precision mismatch | MEDIUM |
| User | users | — | (model field `nickname`) | (no column) | model-only field | HIGH |
| — | audit_logs | — | (no model) | (table exists) | orphan table | LOW |
```
For each drift: entity, expected (code/ORM), actual (DB), severity, impact. Drift findings are first-class (carry `file:line` for the ORM side + the DB object name) and feed the deep tier; the most consequential surface to the lean tier via the Filter.

**Feeds IF-2 (`issues.md`).** The issue layer promotes each drift row to an `ISS-` defect, **consuming this Severity verbatim (never re-deriving it)** plus a base-type-only type-equivalence pass (precision/scale preserved). The drift as a *context fact* may still surface to the lean tier via the Filter; the same drift as an `ISS-` *defect* is deep-tier-only (R9) — the two representations are deduped, never cross-contaminated.

## Outputs
`.ai/docs/current/database-schema.md` (note DB type at top: tables, keys, indexes, procs/triggers/views) and `.ai/docs/current/database-data.md` (volume, column stats, PII-obfuscated samples, quality). Entity↔table reconciliation also feeds the horizontal `data-layer.md` (`horizontal.md`).
