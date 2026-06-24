#!/usr/bin/env python3
"""
db_gate.py — the deterministic, OFFLINE reference implementation of global-rules §R7
(the DB-security hard gate). No DB connection — pure string logic the harness (§44)
can exercise without a database. The live-DB round-trip stays the environment-pending
proof; this proves the *decision logic* is correct and load-bearing.

Three checks, mirroring R7 1–4 (database.md "Gate"):
  1. mask_connection_string(conn)  — never show a password (R7.1).
  2. classify_host(conn)           — REFUSE prod/production/master or a managed-DB
                                     endpoint; ALLOW an obvious local/dev host (R7.3).
  3. is_read_only_query(sql)        — accept SELECT / information_schema / PRAGMA(read)
                                     / EXPLAIN / SHOW / DESCRIBE; reject INSERT / UPDATE
                                     / DELETE / any DDL / multi-statement writes (R7.4).

Safety bias (deliberate): this is a HARD SAFETY gate, so the safe failure is to
REFUSE/REJECT when in doubt. A false-refuse (declining a safe local DB) only annoys;
a false-allow (touching prod, or running a write) is the trust-destroying outcome.
So host classification matches production signals as conservative substrings, and the
query allow-list rejects anything not provably read-only.
"""
from __future__ import annotations

import re

# Managed / cloud production DB endpoints (non-exhaustive — R7 says refuse on ANY
# production signal). Matched as host substrings.
MANAGED_HOST_PATTERNS = [
    "rds.amazonaws.com",        # AWS RDS / Aurora
    "redshift.amazonaws.com",   # AWS Redshift
    "cache.amazonaws.com",      # AWS ElastiCache
    "database.azure.com",       # Azure Database (postgres/mysql/mariadb)
    "database.windows.net",     # Azure SQL
    "cosmos.azure.com",         # Azure Cosmos
    "cloudsql",                 # GCP Cloud SQL (connection name or proxy)
    "googleapis.com",           # GCP managed endpoints
    "mongodb.net",              # MongoDB Atlas
    "supabase.co",              # Supabase
    "neon.tech",                # Neon
    "psdb.cloud",               # PlanetScale
    "planetscale",              # PlanetScale
    "ondigitalocean.com",       # DigitalOcean managed DB
    "oraclecloud.com",          # OCI
    "render.com",               # Render managed PG
    "railway.app",              # Railway
    "aivencloud.com",           # Aiven
    "cockroachlabs.cloud",      # Cockroach Cloud
    "timescale.com",            # Timescale Cloud
]
# Production-name signals anywhere in the connection string (R7.3).
PROD_TOKENS = ["prod", "production", "master"]

# Statement leads that are read-only.
READ_LEADS = {"SELECT", "WITH", "PRAGMA", "EXPLAIN", "SHOW", "DESC", "DESCRIBE", "VALUES"}
# Verbs that write data or change schema — reject if ANY statement leads with one,
# or appears as a statement verb inside a CTE/compound query.
WRITE_LEADS = {
    "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT", "REPLACE",
    "CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME",
    "GRANT", "REVOKE",
    "CALL", "EXEC", "EXECUTE", "DO",
    "ATTACH", "DETACH", "VACUUM", "REINDEX", "ANALYZE",
    "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "SET", "LOCK", "COPY", "LOAD", "IMPORT",
}


def mask_connection_string(conn: str) -> str:
    """Replace the password with **** in URL-style and key=value DSNs (R7.1)."""
    if not conn:
        return conn
    out = conn
    # URL form:  scheme://user:password@host...
    out = re.sub(r"(://[^:/@\s]+:)([^@/\s]+)(@)", r"\1****\3", out)
    # key=value DSN forms:  password=... / pwd=... / passwd=...
    out = re.sub(r"(?i)\b(password|passwd|pwd)\s*=\s*('[^']*'|\"[^\"]*\"|[^;\s]+)",
                 r"\1=****", out)
    return out


def classify_host(conn: str) -> tuple[str, str]:
    """Return ('refuse'|'allow', reason). REFUSE on any production signal (R7.3)."""
    if not conn:
        return ("refuse", "empty connection string")
    low = conn.lower()
    for tok in PROD_TOKENS:
        if re.search(r"(?<![a-z])" + re.escape(tok), low):
            # conservative: catches prod-db, db.prod., myprod, production, master*
            return ("refuse", f"production name signal '{tok}' present")
    for pat in MANAGED_HOST_PATTERNS:
        if pat in low:
            return ("refuse", f"managed/cloud production endpoint '{pat}'")
    return ("allow", "no production signal — local/dev host (still requires y/n confirmation, R7.2)")


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)   # block comments
    sql = re.sub(r"--[^\n]*", " ", sql)                     # line comments
    sql = re.sub(r"(?m)#[^\n]*$", " ", sql)                 # mysql # comments
    return sql


def is_read_only_query(sql: str) -> tuple[bool, str]:
    """Accept provably read-only SQL; reject writes/DDL/multi-statement writes (R7.4)."""
    if not sql or not sql.strip():
        return (False, "empty query")
    clean = _strip_sql_comments(sql)
    statements = [s.strip() for s in clean.split(";") if s.strip()]
    if not statements:
        return (False, "no statement after stripping comments")
    for st in statements:
        lead = re.match(r"\(*\s*([A-Za-z_]+)", st)
        verb = (lead.group(1).upper() if lead else "")
        if verb in WRITE_LEADS:
            return (False, f"write/DDL statement: leads with {verb}")
        if verb not in READ_LEADS:
            return (False, f"non-read statement: leads with {verb or '?'}")
        # tokens of the statement (word-boundary), to catch writes hidden in a CTE/body
        toks = set(re.findall(r"[A-Za-z_]+", st.upper()))
        # SELECT ... INTO  creates a table (T-SQL / pg SELECT INTO) → not read-only
        if verb in ("SELECT", "WITH", "VALUES") and "INTO" in toks:
            return (False, "SELECT…INTO writes a table")
        # any embedded write verb anywhere in the statement (e.g. WITH x AS (…) DELETE …)
        bad = (toks & WRITE_LEADS) - {"SET"}   # 'SET' is part of UPDATE, already gated by the lead check
        if bad:
            return (False, f"embedded write/DDL verb(s): {sorted(bad)}")
        # PRAGMA setter form (PRAGMA x = y) writes config → reject; read PRAGMA is fine
        if verb == "PRAGMA" and "=" in st:
            return (False, "PRAGMA setter (writes config)")
    return (True, "read-only")


def evaluate(conn: str, sql: str) -> dict:
    """Convenience: run all three checks for one (conn, sql) pair."""
    cls, creason = classify_host(conn)
    ro, qreason = is_read_only_query(sql)
    return {
        "masked": mask_connection_string(conn),
        "host_decision": cls, "host_reason": creason,
        "query_allowed": ro, "query_reason": qreason,
        "would_proceed": cls == "allow" and ro,
    }


# ── Plain-language DB card — the R10 face of the R7 gate (database.md) ──
# When a DB is detected, DeepInit offers a live read in PLAIN words — never the internal
# vocabulary the improvised prompt leaked ("ORM-drift (IF-2)", "the R7 gate", "live-drift",
# "information_schema", "EF migrations", "NPoco"). If several environments are configured
# (dev / stage / prod), it first asks WHICH to read. A production / managed-cloud host is
# AUTO-DECLINED to code-only (classify_host == 'refuse'): it is shown but not offered as a
# live target — the R7 hard gate underneath (mask → y/n → refuse-prod → read-only) is
# UNCHANGED; this only governs how the choice is PRESENTED. The recommendation is the
# conservative default — code-only, don't connect (a false-connect is the trust-killer, the
# same safety bias as classify_host). Mirrors the prose in database.md / global-rules R7.
DB_READ_OPTIONS = (
    ("Yes, read it", "live"),                 # live read (still gated by R7 underneath)
    ("No — use the code only", "static"),     # recommended == the safe default: don't connect
)
DB_READ_RECOMMENDED = "static"                # MUST equal the conservative default (R10: recommended == default)


def _env_label(db: dict) -> str:
    """A plain button label for one detected DB config, e.g. 'Dev (app_dev)'."""
    env = str(db.get("env") or "").strip()
    name = str(db.get("name") or db.get("database") or "").strip()
    pretty = env.capitalize() if env else "Database"
    return f"{pretty} ({name})" if name else pretty


def db_prompt_options(detected, assume_yes: bool = False) -> dict:
    """The plain-language DB card: env picker (only when >1 config) + a live/static y/n.

    detected   — list of {env, name, conn} dicts (one per detected DB config). Multiple DBs /
                 environments are common; the picker lets the user choose which to read.
    assume_yes — --yes / --no-confirm (suppress the card; proceed code-only, never auto-connect).

    Returns {prompt, multi_env, env_options, read_options, read_recommended, reason}. Each env
    carries host_decision ('allow'|'refuse' from classify_host) and live_offered — a refused
    (prod / managed-cloud) host is shown but live_offered=False (auto-declined to code-only).
    FAIL-SAFE: no DB or --yes ⇒ no prompt, no connection.
    """
    dbs = [d for d in (detected or []) if isinstance(d, dict)]
    if not dbs or assume_yes:
        return {"prompt": False, "multi_env": False, "env_options": [],
                "read_options": DB_READ_OPTIONS, "read_recommended": DB_READ_RECOMMENDED,
                "reason": "assume_yes" if assume_yes else "no_db"}
    env_options = []
    for db in dbs:
        decision, reason = classify_host(db.get("conn", ""))
        env_options.append({
            "label": _env_label(db),
            "env": str(db.get("env") or "").strip(),
            "host_decision": decision,                 # 'allow' | 'refuse'
            "live_offered": decision == "allow",       # refused (prod/managed) host → auto-declined to code-only
            "reason": reason,
        })
    env_options.append({"label": "Don't read any database", "env": None,
                        "host_decision": "n/a", "live_offered": False, "reason": "user opted out"})
    return {"prompt": True, "multi_env": len(dbs) > 1,
            "env_options": env_options, "read_options": DB_READ_OPTIONS,
            "read_recommended": DB_READ_RECOMMENDED, "reason": "db_detected"}


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) >= 3:
        print(json.dumps(evaluate(sys.argv[1], sys.argv[2]), indent=2))
    else:
        print("usage: db_gate.py <connection_string> <sql>", file=sys.stderr)
        sys.exit(2)
