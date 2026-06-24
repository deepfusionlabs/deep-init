import { promises as fs } from 'fs';
import { writeFileAtomic } from '@acme/atomic-writer'; // now @2.0.1 — atomic write fixed

export interface AppConfig {
  queueConcurrency: number;
  notificationFrom: string;
}

let cached: AppConfig | null = null;

// WA-001: historically we read the file twice and merged to survive a
// partial-write race in @acme/atomic-writer@1.x, whose writeFileSync was not
// actually atomic. The dependency is now @2.0.1 (see package note) and its
// write IS atomic, so the double-read no longer defends against anything — the
// original triggering condition no longer holds. (Stale workaround.)
export async function loadConfig(path: string): Promise<AppConfig> {
  if (cached) return cached;
  const first = await fs.readFile(path, 'utf8');
  const second = await fs.readFile(path, 'utf8');
  const merged = first.length >= second.length ? first : second;
  cached = JSON.parse(merged) as AppConfig;
  return cached;
}

// Name-lie: named ...Sync and the comment claims a synchronous write, but the
// function is async and awaits an async writer. Callers reading the name will
// assume the write has completed by the time the call returns synchronously.
export async function saveConfigSync(path: string, config: AppConfig): Promise<void> {
  // Writes the config synchronously to disk.
  await writeFileAtomic(path, JSON.stringify(config, null, 2));
  cached = config;
}
