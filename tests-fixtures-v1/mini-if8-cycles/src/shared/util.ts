// shared is a leaf: it imports no other component, so catalog -> shared is acyclic.
export function slug(s: string) {
  return s.toLowerCase().replace(/\s+/g, '-');
}
