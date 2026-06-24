import { LEGACY_MODE } from '../config/build';
export function process() {
  if (!LEGACY_MODE) {
    return useNewPath();
  }
  return useLegacyPath();
}
function useNewPath() { return 1; }
function useLegacyPath() { return 0; }
