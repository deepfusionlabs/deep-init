# Security Policy

DeepInit is a **100% local, read-only** code-analysis skill — it runs in your Claude Code session, reads your repository, and writes only documentation files (the `CLAUDE.md` owned region and `.ai/docs/` — plus, only when a non-Claude-Code consumer such as Cursor/Copilot/Windsurf is present, a conditional `AGENTS.md` cross-tool export). It opens no servers and sends no data off your machine. The attack surface is correspondingly small, but we take reports seriously.

## Reporting a vulnerability

Please report privately — **do not** open a public issue for a security report.

- **Email:** elad@deepfusionlabs.ai

Include: a description, affected file(s)/stage, reproduction steps, and impact. We aim to acknowledge within a few business days and will coordinate a fix and disclosure timeline with you.

Prefer not to email? Use GitHub's **[Private Vulnerability Reporting](https://github.com/deepfusionlabs/deep-init/security/advisories/new)** — open the repository's **Security → Report a vulnerability** tab and your report stays private to the maintainers.

## Supported versions

| Version | Supported |
|---------|-----------|
| Latest `0.x` minor release | ✅ |
| Anything older | ✗ (upgrade) |

Only the latest minor release is supported — please upgrade before reporting. The current version is recorded in `package.json` / `.claude-plugin/plugin.json` (we deliberately do not duplicate the number here, to avoid drift).

## Scope notes

- **R7 database gate.** DeepInit only ever connects to a database after masking the connection string, confirming with you, refusing production hosts, and issuing **READ-ONLY** queries (`SELECT` / `information_schema`). A report of any write, any unconfirmed connect, or any prod-host connect is in scope and high priority.
- **Redaction.** All emitted output passes an unconditional secret/PII redaction gate before being written. A secret or PII value leaking into `CLAUDE.md`, `.ai/docs/`, `issues.md`, the conditional `AGENTS.md` export, `dashboard.html`, or `deepinit.sarif` is in scope.
- **Report-only.** The issue layer and `--heal` never modify your source (hardcoded floor). A path that mutates source is in scope.
