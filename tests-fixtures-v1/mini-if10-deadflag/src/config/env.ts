// config/env.ts — NON-LITERAL trap: DEBUG is config-determined at runtime (process.env), NOT a
// compile-time constant. The literal-const binding never matches → predicate FALSE. Must NOT fire.
const DEBUG = process.env.NODE_ENV === 'production';

export function log(msg: string): void {
  if (DEBUG) {
    emit(msg);
  }
}
declare const process: { env: Record<string, string> };
declare function emit(m: string): void;
