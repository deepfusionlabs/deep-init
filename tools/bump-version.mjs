#!/usr/bin/env node
/**
 * tools/bump-version.mjs — single-source version bump for a MANUAL-versioning repo.
 *
 * Seeded by oss-kit as the companion to `process.releaseTool: "manual"` — the middle
 * option between full release-it git automation and nothing. It deterministically syncs
 * the version across the files that drift when bumped by hand (the manifests + the README
 * status token + a CHANGELOG stub), validates a clean FORWARD semver bump, and PRINTS the
 * git tag command for YOU to run — it NEVER touches git (history stays manual, matching the
 * oss-kit Working agreement: agents/scripts draft, the human commits). Node stdlib only.
 *
 * Usage:  node tools/bump-version.mjs <X.Y.Z> [--date YYYY-MM-DD]
 * Exit:   0 ok · 1 usage/validation error
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// tools/.. = repo root (robust regardless of CWD; override with $BUMP_ROOT for testing).
const ROOT = process.env.BUMP_ROOT || dirname(dirname(fileURLToPath(import.meta.url)));
const args = process.argv.slice(2);
const newVer = args.find(a => !a.startsWith("--"));
const dateArg = args.includes("--date") ? args[args.indexOf("--date") + 1] : null;

function die(msg) { console.error(`[bump-version] ${msg}`); process.exit(1); }
// Accept an optional -prerelease/+build suffix; compare only the X.Y.Z CORE (so a
// prerelease-versioned repo can still be bumped + chosen as the version authority).
const parse = v => { const m = /^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$/.exec((v || "").trim()); return m ? m.slice(1, 4).map(Number) : null; };
const cmp = (a, b) => { for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] - b[i]; return 0; };
const readJson = f => { try { return JSON.parse(readFileSync(f, "utf8")); } catch (e) { return null; } };

const np = parse(newVer);
if (!np) die(`usage: node tools/bump-version.mjs <X.Y.Z> [--date YYYY-MM-DD]  (got: ${newVer ?? "nothing"})`);
if (dateArg && !/^\d{4}-\d{2}-\d{2}$/.test(dateArg)) die(`--date must be YYYY-MM-DD (got: ${dateArg})`);

// Version authority: package.json if present, else a Claude-plugin manifest. The repo's
// manifests are the real drift source; the authority is the one we read "current" from.
const MANIFESTS = [
  join(ROOT, "package.json"),
  join(ROOT, ".claude-plugin/plugin.json"),
  join(ROOT, ".claude-plugin/marketplace.json"),
].filter(existsSync);
const authority = MANIFESTS.find(f => parse((readJson(f) || {}).version));
if (!authority) die(`no manifest with a valid "version" found (looked for package.json / .claude-plugin/*.json). Run from the repo root.`);

const curStr = readJson(authority).version;
const cur = parse(curStr);
if (cmp(np, cur) <= 0) die(`new version ${newVer} must be greater than current ${curStr} (no down/equal bumps)`);

const date = dateArg || new Date().toISOString().slice(0, 10);
const minorOrMajor = np[0] !== cur[0] || np[1] !== cur[1];
const changed = [];

// 1) every manifest that carries a version
for (const f of MANIFESTS) {
  const j = readJson(f);
  if (!j || !("version" in j)) continue;
  j.version = newVer;
  writeFileSync(f, JSON.stringify(j, null, 2) + "\n");
  changed.push(f.slice(ROOT.length + 1).replace(/\\/g, "/"));   // forward-slash display on every OS
}

// 2) README version token — minor/major only (patch leaves the status line). Rewrite the
// token ONLY on a Status/Version line (bounded), NEVER blanket over the whole file: a
// blanket split/join would also rewrite changelog links, release URLs, and prose that must
// keep their historical versions. Warn about any other occurrence rather than touch it.
const README = join(ROOT, "README.md");
if (existsSync(README)) {
  if (minorOrMajor) {
    const before = readFileSync(README, "utf8");
    const esc = curStr.replace(/[.+]/g, "\\$&");
    const lineRe = new RegExp("^([^\\n]*\\b(?:Status|Version)\\b[^\\n]*?)\\bv" + esc + "\\b", "mi");
    if (lineRe.test(before)) {
      writeFileSync(README, before.replace(lineRe, "$1v" + newVer));
      changed.push("README.md");
      const others = (before.match(new RegExp("\\bv" + esc + "\\b", "g")) || []).length - 1;
      if (others > 0) console.warn(`[bump-version] README: updated the status line; left ${others} other "v${curStr}" mention(s) as-is (review them)`);
    } else {
      console.warn(`[bump-version] README: no "Status/Version … v${curStr}" line found — update the status line manually`);
    }
  } else {
    console.log(`[bump-version] README: skipped (patch bump — status line left unchanged)`);
  }
}

// 3) CHANGELOG — insert a dated stub above the newest versioned section (or append)
const CHANGELOG = join(ROOT, "CHANGELOG.md");
if (existsSync(CHANGELOG)) {
  const cl = readFileSync(CHANGELOG, "utf8");
  const m = /^## \[?\d/m.exec(cl);
  const block = `## [${newVer}] — ${date}\n\n### Changed\n- _Summarize this release; replace this line._\n\n---\n\n`;
  writeFileSync(CHANGELOG, m ? cl.slice(0, m.index) + block + cl.slice(m.index) : `${cl}\n${block}`);
  changed.push("CHANGELOG.md");
}

// 4) version-canary command — keep the LOADED-version literal current (harness §69 asserts it
// equals the manifest; the bump prevents drift). Bounded to the single marked canary line.
const VERSION_CMD = join(ROOT, "commands/version.md");
if (existsSync(VERSION_CMD)) {
  const before = readFileSync(VERSION_CMD, "utf8");
  const canaryRe = /^.*deepinit:loaded-version.*$/m;
  if (canaryRe.test(before)) {
    const after = before.replace(canaryRe, line => {
      const updated = line.replace(/v\d+\.\d+\.\d+/, "v" + newVer);
      if (updated === line) die(`commands/version.md: canary line found but no vX.Y.Z literal to bump; restore the format (e.g. "**DeepInit v${newVer}** <!-- deepinit:loaded-version -->"). Found: ${line.trim()}`);
      return updated;
    });
    writeFileSync(VERSION_CMD, after);
    changed.push("commands/version.md");
  } else {
    die(`commands/version.md: no "deepinit:loaded-version" canary line found; the loaded-version source of truth (harness §69) cannot be synced. Restore the marker or fix the regex.`);
  }
}

console.log(`[bump-version] ${curStr} -> ${newVer}  (updated: ${changed.join(", ") || "nothing"})`);
console.log(`[bump-version] Review the diff + fill the CHANGELOG entry, then YOU run git (this script never does):`);
console.log(`  git add -A && git commit`);
console.log(`  git tag -a v${newVer} -m "v${newVer} - <summary>"`);
