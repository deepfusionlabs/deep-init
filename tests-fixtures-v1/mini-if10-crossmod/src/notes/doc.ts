import { STRFLAG } from '../flagdefs/defs';
// @example  if (STRFLAG) { ... }
export function doc(cfg: { flag: boolean }) {
  log("branch guarded by if (STRFLAG)");
  if (cfg.flag) {
    return 1;
  }
  return 0;
}
function log(_: string) {}
