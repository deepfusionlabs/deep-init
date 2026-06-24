# triggers.md — keeping the docs fresh (proactive session-start suggestion + opt-in auto)

The mechanics of *when* DeepInit tells you the docs have fallen behind, and when `--update` runs.
The honest constraint, stated plainly: **a git hook cannot summon a Claude session, and the skill is
`disable-model-invocation: true`** — so nothing re-analyses a repo on its own. What the triggers do
is make staleness **visible and one keystroke away** (free, 0 tokens), and — opt-in — wire a real
headless run. The reliable, visible surface is the **session suggestion** — injected on *both*
`SessionStart` (a session opens) and `UserPromptSubmit` (the user submits a prompt), so the offer
re-surfaces at the first prompt and catches staleness that appears mid-session; everything else is
secondary.

```
session suggestion             →   commit breadcrumb        →   auto-update (opt-in, off)
(SessionStart + UserPromptSubmit:   (post-commit records +        (a detached headless `claude -p`
 docs stale → the agent OFFERS a    optionally nudges in the      runs --update after a source commit;
 one-click refresh, FIRST, showing  terminal — invisible in       never auto-commits)
 WHAT changed; once per session)    the VS Code commit UI)
```

The first two are **0-token, deterministic** (they shell out to `assets/deepinit_status.py`, never to
a model). Only **auto-update** spends tokens and writes files — so it is **off by default**.

## The keystone — `assets/deepinit_status.py` (deterministic, no LLM, no network)
The hook-callable core of `--lint`. It locates the generated baseline (`.ai/docs/.file_hashes.json`,
the current flat layout, **or** `.ai/docs/current/.file_hashes.json`), parses any of the three on-disk
shapes (flat `{path: sha}`, wrapped `{"files": …}`, or per-component `{"components": …}`), and reports
drift — **modified** (a file's sha changed), **removed** (a stored file absent on disk — caught by
iterating the STORED set, the `update.md` Step-0 symmetric set-diff, harness §64), and **pending** (the
`.pending_changes.txt` advisory). Exit 0 = fresh or no-state (never errors on a fresh checkout), 1 =
stale. Because a git/Session hook can't run Claude, this Python keystone is what makes the proactive
surfaces real. (Harness §65.)

## Session suggestion — the primary surface (plugin-shipped; active on install)
DeepInit ships **plugin-level hooks** (`hooks/hooks.json`) that fire the same `assets/session-start.sh`
on **two** events — **`SessionStart`** (a session opens) and **`UserPromptSubmit`** (the user submits a
prompt) — so it is active in any repo where the plugin is enabled with **no per-repo setup**. Why both:
a `SessionStart`-only hook injects context the agent often skips when the user's first message is a task,
and Claude Code **drops a hook's `systemMessage` in the VS Code UI** — so the *reliable* surface is the
agent acting on `additionalContext` at the `UserPromptSubmit` injection point (the freshest, right before
the agent answers), with `SessionStart` as the opening nudge. Both share **one** cadence gate, so the
offer still appears **at most once per session**. On either event it:
1. self-gates — silent if the repo has no DeepInit state, if disabled (below), or if it already nudged
   for this session. The cadence (`notify-cadence`, default **session**) decides "already nudged":
   **session** = once per NEW session — it dedups on the `session_id` (from the hook's stdin JSON, carried
   by both events), so an actively-committing dev is nudged each genuinely-new session but never twice
   within one (resume/compact/clear and every later prompt stay silent); **window** = at most once per
   `notify-window-hours` (default 6h) wall-clock; **always** = every session start / prompt while stale.
   (No `session_id` — older Claude Code — falls back to the 6h window.) The last-nudged session id (or
   timestamp, for window/fallback) lives in the gitignored `.ai/.deepinit-nudge-state`. The cheap gate runs
   **before** the tree-hashing status check, so an already-nudged session never re-hashes on every prompt;
2. else it runs the 0-token status check and, if **stale**, emits an `additionalContext` payload (with
   `hookEventName` matching the invoking event — required for Claude Code to accept it) telling the agent
   that its **FIRST action, before addressing the user's request, MUST be to OFFER a refresh** — *a hook
   can only inject text, it cannot draw a button*, so the agent presents the choice via **AskUserQuestion**
   and the payload lists **what changed** (the modified/removed/pending paths + owning components, not just
   a count):
   **[Update now]** → run `/deep-init:refresh` · **[Not now]** → nothing · **[Don't ask in this repo]**
   → create the `.claude/.deepinit-no-nudge` flag.
   It **NEVER** runs the (costly) update itself — the user chooses; on **[Update now]** the update runs
   in-session.

## Disable / tune — any one of these
- **The safe button way:** `/deep-init:customize` → **Freshness & notifications** — buttons for off /
  cadence / time-window / breadcrumb / auto-update; on confirm it persists the keys below via the
  surgical writer `tools/freshness_config.py` (the one place a DeepInit invocation writes config — see
  *Configuration*). No flags, no hand-edits, no typos.
- **Per-repo, one keystroke:** the **[Don't ask in this repo]** choice (or the "Pause in this repo"
  button) creates `.claude/.deepinit-no-nudge` (gitignored). Delete it to re-enable. (You can also just
  `touch .claude/.deepinit-no-nudge`.)
- **Config:** `notify-on-session-start: "off"` (or the back-compat `check-on-session-start: "off"`) in
  `.ai/deepinit.config`. Change *how often* (not whether) with `notify-cadence` / `notify-window-hours`.
- **Whole plugin:** `claude plugin disable deep-init`.
- **All hooks:** `disableAllHooks: true` in `~/.claude/settings.json` (global) or
  `.claude/settings.local.json` (per-project, gitignored).
- **Self-quieting:** at most once per session (default cadence) even when left fully on.

Every off-switch silences **both** events — the disable checks and the cadence gate live in the one shared
`session-start.sh`, before any payload is emitted, so `notify-on-session-start` governs the whole in-session
suggestion (both `SessionStart` and `UserPromptSubmit`), not just the opening one.

## Why these triggers, and not the others (the Claude Code environment)
- **SessionStart → chosen.** Fires once per session, can inject context the agent acts on, plugin-shippable.
  The opening nudge a VS Code + Claude Code user sees. (Requires Claude Code v2.0+.)
- **`UserPromptSubmit` → chosen (the reliability surface).** Fires right before the agent answers, so its
  `additionalContext` is the *freshest* — the agent acts on it instead of skipping a session-open note to
  do the user's first task — and it catches staleness that appears **mid-session** (e.g. just after a
  commit). It is **not** the rejected per-message nudge below: the **shared once-per-session cadence gate**
  makes it fire at most once per session, exactly like `SessionStart`, not on every prompt.
- **Per-message (`Stop`) → rejected.** It fires after *every* reply with no natural dedup — the fastest way
  to make a user disable the whole feature. Over-notifying is the only real failure mode of a proactive
  nudge; the `UserPromptSubmit` surface avoids it precisely *because* it shares the session cadence gate.
- **`PreCompact` (before context compaction) → optional bonus, not wired.** Rare (~once in a long session);
  a fine place to gently re-surface. Wireable by adding it to `hooks/hooks.json`; left out for now to keep
  the surface minimal.
- **`SessionEnd` → evaluated, omitted.** The session is closing, so the user can't act, and there's nothing
  to record that the next SessionStart check doesn't recompute. A do-nothing hook is clutter.
- **`Notification` hook → unusable.** It only *reacts* to Claude's own notifications; a plugin can't use it
  to start one.

## commit breadcrumb (`setup-hooks`, optional)
`setup-hooks` installs `assets/post-commit.sh` into `.git/hooks/`: it appends changed files to
`.ai/docs/current/.pending_changes.txt` (an advisory accelerator for the next `--update`) and, for a
**source** commit only (skip commits touching only `.md`/`.css`/config/lockfiles), can print a one-line
nudge. **Honest caveat:** a post-commit hook prints to the *terminal* of `git commit` — committing
through the VS Code Source Control UI does **not** surface it. So this is a background breadcrumb / CI
signal, **not** the thing you'll see; the SessionStart suggestion is. It never blocks or fails the commit.

## auto-update (default OFF — the only token-spending trigger)
When `auto-update` is on, `post-commit.sh` spawns a **detached headless** `claude -p "/deep-init:refresh"`.
Six safeguards make it safe to leave on:
1. **Detached / backgrounded** so `git commit` never hangs on the analysis (cross-platform: Git-Bash
   `nohup … &` / Windows `start //b`).
2. **Lockfile** (`.ai/docs/current/.update.lock`) so two quick commits can't launch overlapping runs that
   race the same `.ai/docs`.
3. **PATH / auth resolution + graceful skip** — if `claude` isn't found or isn't authenticated, log one
   line and skip; never error-spew from a post-commit hook.
4. **Never auto-commits** — it writes the refreshed docs to the owned regions + a dated `.bak` and **leaves
   a dirty tree** for the human to review and commit (the repo's draft-only discipline).
5. **Source-gated** — same skip rule as the breadcrumb (docs/config/lockfile-only commits don't trigger).
6. **Documented token cost** — every qualifying commit spends a model run; that cost is exactly why it is
   opt-in, not a default. The DP-1 skip keeps each run small.

## Configuration — `.ai/deepinit.config` (the existing config; no new file)
Trigger settings are ordinary config keys (long-flag names, no `--`), resolved with the usual precedence
(defaults → `.ai/deepinit.config` → inline flags):
- `notify-on-session-start` — default **on** — the proactive in-session suggestion (primary); governs
  **both** the `SessionStart` and `UserPromptSubmit` surfaces (one shared gate). The name is kept for
  back-compat; `check-on-session-start` is an alias.
- `notify-cadence` — default **session** — how often the suggestion re-fires while stale (across both
  events): `session` (once per new session) · `window` (once per `notify-window-hours`) · `always`.
- `notify-window-hours` — default **6** — the back-off window for `notify-cadence: "window"` (ignored otherwise).
- `notify-on-commit` — default **on** — the post-commit terminal breadcrumb (secondary).
- `auto-update` — default **off** — the opt-in headless run above.

**Who writes these.** `.ai/deepinit.config` is read-only input to a *run* — DeepInit never writes it during
analysis. The single exception: the user-invoked `/deep-init:customize` → Freshness step, which on an
explicit confirmation persists just these freshness keys through `tools/freshness_config.py` — a surgical,
schema-validating upsert that leaves every other key, comment, and layout untouched. A *settings* command
may write; a *run* may not.
