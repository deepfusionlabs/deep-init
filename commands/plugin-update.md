---
description: Upgrade DeepInit to the latest version — pulls the newest from the marketplace (on one confirm), then guides the host-correct reload. Ends the "is my plugin stale?" dance.
---

Bring the running DeepInit up to date. Claude Code has no first-party "pull the latest plugin" command — the request ([anthropics/claude-code#38271](https://github.com/anthropics/claude-code/issues/38271)) was **closed as not-planned**, so this command IS that flow. Do this:

1. **Detect the install kind:**
   - **Marketplace install** (the plugin loads from `~/.claude/plugins/`) → go to step 2.
   - **Local dogfood** (you're running this repo's `skills/deep-init/` directly) → there is nothing to fetch; skip to step 4 (a reload just picks up your local edits).

2. **Detect your host first — it changes BOTH how you update and how you activate.** Read your runtime host from your system context (e.g. a note that you're "running inside a VSCode native extension environment"), then follow **only** the matching block. Resolve the target `deep-init@<marketplace>` — read the marketplace alias from the installed plugin state under `~/.claude/plugins/`, else fall back to the `name` in `.claude-plugin/marketplace.json`.

   - **VS Code / JetBrains extension** → the chat panel does **not** shell out and the `claude` CLI is **not on its PATH**, so do **not** present a bare-shell `claude plugin update` here. Update through the in-extension UI: open the **`/plugin`** manager → **Plugins tab** → select `deep-init` → **Update / reinstall**.
   - **Plain terminal / CLI** → refresh the catalog FIRST, then update, in the shell:
     ```
     /plugin marketplace update <marketplace>      # refresh the catalog so the newest version is visible
     claude plugin update deep-init@<marketplace>  # pull the newest to disk (reversible; updates installed_plugins.json)
     ```
     **Refresh first, or the update quietly does nothing:** if the catalog isn't refreshed, `claude plugin update` compares against the stale advertised version, treats the old one as newest, and **silently no-op**s with no error — you'll believe it updated when nothing changed. If it reports "nothing to update" but the version didn't move, re-run the `marketplace update` and try again.
   - **Desktop app / web** → there's no shell either; update through the **`/plugin`** manager (select `deep-init` → Update / reinstall), same as the extension.

3. **Confirm before changing anything.** State exactly what will run and that it changes **host plugin state** (not your repo, not git, reversible). Then **WAIT for an explicit yes** — never run it on assumption. On yes, perform the update for the detected host — run `claude plugin update deep-init@<marketplace>` via the shell only in the **plain terminal**; in every other host drive the `/plugin` UI — and report the old → new version.

4. **Activate it — the one step left for you (a command can't self-invoke a reload).** The update pulled the new version **to disk**; it is **staged but not yet running**, because Claude Code loads plugin markdown ONCE per session. Your single remaining action depends on your host:
   - **Plain terminal / CLI** → run **`/reload-plugins`**, or (more reliable for a command/version flip) start a **new session**. A reload picks up skills and hooks but does not rebuild the slash-command index ([#37862](https://github.com/anthropics/claude-code/issues/37862)), so the version canary may not flip from it — a new session is the sure path.
   - **VS Code / JetBrains extension** → **restart the IDE itself** — a full quit + reopen. `Developer: Reload Window` **does not reload the plugin host** (nor does opening a new chat in the same window), so the freshly-updated version stays invisible until a true app restart.
   - **Desktop app / web** → fully **restart the app** (or reload the session) — a window reload alone is not enough.

5. **Confirm it flipped.** After you reload/restart, run **`/deep-init:version`** — the **LOADED** line should now equal the on-disk version (it reports what's actually running, so it's the honest check that activation worked).

For a full active-vs-installed-vs-newest diagnosis across every plugin (and duplicate-shadow detection), `/oss-kit:oss-plugin-doctor` owns that.

$ARGUMENTS
