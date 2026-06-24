type Level = 'info' | 'warn' | 'error';

function log(level: Level, msg: string, meta?: Record<string, unknown>): void {
  const line = { level, msg, ...meta, at: new Date().toISOString() };
  // eslint-disable-next-line no-console
  console[level === 'error' ? 'error' : 'log'](JSON.stringify(line));
}

export const logger = {
  info: (msg: string, meta?: Record<string, unknown>) => log('info', msg, meta),
  warn: (msg: string, meta?: Record<string, unknown>) => log('warn', msg, meta),
  error: (msg: string, meta?: Record<string, unknown>) => log('error', msg, meta),
};
