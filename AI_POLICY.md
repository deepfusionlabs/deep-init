# AI Policy

This project (`DeepInit`) is developed with AI assistance. This document discloses how, where, and under what guardrails AI is used in the development of this codebase.

## Tools used

- **Claude Code** (Anthropic) — primary AI development assistant, run locally by maintainers. Used for code authoring, refactoring, test generation, documentation, and code review.
- List any additional AI tools (Copilot, Cursor, etc.) that commit to this repository. If a tool is added later, update this file **before** the new tool's first commit.

## What kinds of changes get AI assistance

AI assistance is used across most categories of change in `DeepInit`:

- Source code — bug fixes, refactoring, new features
- Test suite — writing assertions, fixing flakes, expanding coverage
- Governance and policy documents (this file, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`)
- CI workflows (`.github/workflows/*.yml`)
- Documentation (`README.md`, `docs/`)

Security-sensitive changes (auth, crypto, secret handling, release tooling) receive **extra scrutiny** during human review — see below.

## Human review policy

- **Every** AI-assisted change is reviewed by a human maintainer before it lands on the default branch.
- AI agents do **not** run `git commit`, `git push`, `git merge`, or any other history-writing operation in this repository — maintainers perform all git operations manually after diff review.
- Security-sensitive changes additionally require:
  - A green CI run, including any security scanners configured for this repo (Snyk, Socket, Dependency Review, CodeQL, gitleaks).
  - A reviewer who did not co-author the change with AI in the same session, where practical.
- AI-generated code that fails CI is not merged; the AI's output is treated as a draft, not a deliverable.

## Quality standards

- AI-generated code must pass the full test suite locally and in CI before merge.
- AI-generated code must follow the conventions documented in `CONTRIBUTING.md`.
- AI-generated commit messages must follow Conventional Commits and be reviewed (and typically edited) by a human before use.
- AI may draft commit messages but must never execute the commit.

## Provenance and attribution

- Commits authored with AI assistance are made under the maintainer's own git identity. Co-author trailers may be added at the maintainer's discretion.
- If this repo adopts a separate `AI-Assisted-By:` trailer convention, this file will be updated to document it.

## Contact

Questions about this policy, or concerns about a specific AI-assisted change:

- **Email:** elad@deepfusionlabs.ai
- **Repository:** https://github.com/deepfusionlabs/deep-init

This policy was last reviewed on 2026-06-09.
