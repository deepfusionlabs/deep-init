---
description: Which DeepInit version is actually running right now? Prints the LOADED version, checks it against the on-disk version, and tells you if you need to reload. No analysis.
---

Report the running DeepInit version — fast, no analysis. Do exactly this, then stop:

1. State the **loaded** version verbatim. This line ships inside the plugin markdown that is actually loaded in your session, so it is the source of truth for "what is running right now":

   **DeepInit v0.5.1** <!-- deepinit:loaded-version -->

2. Read the **on-disk** version (best-effort — skip gracefully if a path isn't present):
   - a local clone of this repo → `.claude-plugin/plugin.json` (the `"version"` field)
   - the marketplace-installed copy → the newest `plugin.json` under `~/.claude/plugins/` (the active pin is recorded in `~/.claude/plugins/installed_plugins.json`; a newer copy in the cache that the pin hasn't moved to means the update was fetched but not yet applied)

3. Compare and advise:
   - **loaded == on-disk** → "You're running the latest version — you're all set."
   - **loaded is behind on-disk** → "The running plugin is STALE: a newer version is on disk but not live. Claude Code loads plugin markdown **ONCE per session** and does not re-read it mid-session, so one activation step remains — and it depends on your host. **Detect your host first** (from your system context), then do only the matching one:
     - **Plain terminal / CLI** → run `/reload-plugins`, or (more reliable for a version/command flip) start a **new session**. A reload picks up skills and hooks but doesn't rebuild the slash-command index, so this canary may not flip from `/reload-plugins` alone — a new session is the sure path.
     - **VS Code / JetBrains extension** → **restart the IDE itself** (a full quit + reopen). `Developer: Reload Window` **does not reload the plugin host**, so the loaded number won't flip from a window reload (or a new chat in the same window).
     - **Desktop app / web** → fully restart the app (or reload the session) — a window reload alone is not enough.

     Then run `/deep-init:version` again to confirm the **LOADED** number flipped (it reports what's actually running, so it's the honest check that activation worked)."
   - **on-disk not found** → just report the loaded version.

For a full active-vs-installed-vs-newest diagnosis across every plugin (and duplicate-shadow detection), run `/oss-kit:oss-plugin-doctor`.

$ARGUMENTS
