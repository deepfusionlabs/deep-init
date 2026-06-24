# redaction.md — C5 Redactor (secret/PII gate)

A hard gate over **all** content before any file is written. Runs unconditionally — the built-in regex + entropy scan always runs, and `gitleaks`/`trufflehog` are used additionally if installed (prefer `gitleaks`, MIT). No secret or PII reaches any output file.

## Secrets (built-in, no external dependency required)
Scan all to-be-emitted content for: high-entropy strings (base64/hex tokens), API-key shapes (`AKIA…`, `sk-…`, `ghp_…`, `xox[baprs]-…`), connection strings with embedded credentials, private-key headers (`-----BEGIN … PRIVATE KEY-----`), JWTs, `.env`-style `KEY=secret` pairs. Any match → replace with `[CREDENTIAL_REDACTED]`. If `gitleaks`/`trufflehog` is present, run it too and union the findings.

## PII obfuscation (mandatory for ALL data samples)
Before writing ANY data from database queries, apply:

| Data type | Detection (column/field names) | Obfuscation |
|-----------|-------------------------------|-------------|
| Person names | first_name, last_name, full_name, author, *_name | `Person_001`, `Person_002` (sequential) |
| Email | email, mail, contact_email | `user_001@example.com` |
| Phone | phone, mobile, tel, cell | `+XXX-XXX-XXXX` |
| Address | address, street, city (with street) | `[ADDRESS_REDACTED]` |
| National IDs | id_number, ssn, teudat_zehut, identity, passport | `[ID_REDACTED]` |
| Date of birth | birth_date, dob, date_of_birth | keep year+month, redact day: `1990-03-XX` |
| Financial (tied to a person) | salary, payment, amount, balance, price | range: `₪[500-1000]` / `$[100-500]` |
| IP address | ip, ip_address, remote_addr | `XXX.XXX.XXX.XXX` |
| Free text (may contain PII) | notes, comments, description, bio, about | `[TEXT_REDACTED - {N} chars]` |
| Passwords/tokens | password, token, secret, api_key | `[CREDENTIAL_REDACTED]` |
| Username/login | username, login, handle | `user_001` |

## Rules
1. Obfuscate BEFORE writing to any file — never write raw PII to disk.
2. Referential consistency: the same person gets the same `Person_NNN` across all tables in one output.
3. Preserve data types + approximate lengths for realistic samples.
4. Non-PII columns (status, type, created_at, counts, IDs) stay unchanged.
5. Hebrew free text: `[TEXT_REDACTED_HE - {N} chars]`.
6. **When in doubt, redact.** A false-positive obfuscation is safe; a false-negative is not.

## Key-value / NoSQL
PII can hide in key *names* and values: `user:john@email.com:sessions` → `user:user_001@example.com:sessions`; `profile:12345678` (national ID) → `profile:[ID_REDACTED]`. When listing key patterns, show structure (`user:{email}:sessions`), not actual values. Document fields follow the column-name rules above.

## Gate behavior
The Redactor is the last thing between findings and disk. If a finding can't be emitted without exposing a secret/PII it can't be cleaned by the rules above, drop the offending value (not the whole finding) and note `[REDACTED]` in place. This stage has no opt-out.
