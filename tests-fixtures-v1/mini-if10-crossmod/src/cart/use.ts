import { FORKED } from '../forkflags';
import { DEADEND } from '../forkflags';
import { MODE } from '../newflags/mode';
export function use() {
  if (FORKED) { doFork(); }
  if (DEADEND) { doDead(); }
  if (MODE) { doMode(); }
}
function doFork() {} function doDead() {} function doMode() {}
