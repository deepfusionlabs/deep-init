// access/roles.ts — NON-ENUMERABLE trap A: Roles is computed at runtime (Object.values), so its
// membership cannot be statically enumerated. Because one side of the Roles pair is non-enumerable,
// the detector degrades the WHOLE comparison (AF-2) rather than diff a full set against a partial
// one. Must NOT fire.
declare const roleMap: Record<string, string>;
export const Roles = Object.values(roleMap);
