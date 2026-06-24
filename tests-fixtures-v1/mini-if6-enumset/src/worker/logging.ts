// worker/logging.ts — SAME-VALUE clone trap B: identical membership to api's LogLevel. Same name,
// same members → agreed duplication (jscpd's territory), NOT a divergence. Must NOT fire.
export type LogLevel = 'debug' | 'info' | 'error';
