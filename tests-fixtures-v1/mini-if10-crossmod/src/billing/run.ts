import { TOGGLE } from '../mutflags/m';
import { DEBUG } from '../cfg/env';
import { MODE2 } from '../cfg/env';
export function run(user: { isAdmin: boolean }) {
  if (TOGGLE) { a(); }
  if (DEBUG) { b(); }
  if (MODE2 === 'on' && user.isAdmin) { c(); }
}
function a() {} function b() {} function c() {}
