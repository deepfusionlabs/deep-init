// VALID: imports only fetchUser, which core/repo exports. Must NOT fire.
import { fetchUser } from '../core/repo';

export function render(id: string) {
  return fetchUser(id).name;
}
