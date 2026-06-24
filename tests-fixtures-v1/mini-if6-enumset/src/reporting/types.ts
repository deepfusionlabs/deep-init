// reporting/types.ts — DERIVATION trap: ReportStatus is explicitly DERIVED from OrderStatus
// (a deliberate widening), referencing it by name. A syntactic link to the base set means the
// difference is intended, not an accidental re-definition. Must NOT fire.
import type { OrderStatus } from '../payments/status';
export type ReportStatus = OrderStatus | 'archived';
