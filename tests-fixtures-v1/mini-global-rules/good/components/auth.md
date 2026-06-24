<!-- provenance: stage=extract component=auth run=run-001 inputs=src/auth date=2026-06-14 -->
# auth (deep tier)

- BR-auth:002 Refresh tokens are single-use and rotated on each use [HIGH] (src/auth/refresh.ts:18)
- IP-auth:001 The session store is keyed by a hashed token id [MEDIUM] (src/auth/store.ts:7)
