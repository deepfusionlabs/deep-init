// admin/roles.ts — NON-ENUMERABLE trap B: a static Roles list. Its sibling (access/roles.ts) is
// non-enumerable, so the whole Roles name degrades — comparing this full set against a partial one
// would manufacture a spurious symmetric difference. Must NOT fire.
export const Roles = ['admin', 'user'];
