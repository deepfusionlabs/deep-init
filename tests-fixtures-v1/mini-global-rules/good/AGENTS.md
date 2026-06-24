<!-- DEEPINIT:START -->
<!-- provenance: stage=emit component=root run=run-001 inputs=src/ date=2026-06-14 -->
# Project context (lean tier)

## Business rules
- BR-auth:001 Access tokens expire after 15 minutes [HIGH] (src/auth/token.ts:42)
- WF-boot:001 Startup loads config before serving traffic [MEDIUM] (src/main.ts:10)
<!-- DEEPINIT:END -->
