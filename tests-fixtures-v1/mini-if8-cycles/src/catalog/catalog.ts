import { slug } from '../shared/util';

// catalog -> shared : a one-way (acyclic) dependency; shared imports nothing back.
export function listProducts() {
  return slug('all-products');
}
