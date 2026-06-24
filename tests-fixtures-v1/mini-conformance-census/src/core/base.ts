// Shared base constructs the documented conventions (ADR-100/101/104) range over.
export class BaseRepository {
  protected query(table: string, id: string) {
    return { table, id };
  }
}

export class BaseService {
  protected run(op: string, arg: unknown) {
    return { op, arg };
  }
}

export class LegacyService {
  protected run(op: string, arg: unknown) {
    return { op, arg, legacy: true };
  }
}

export interface Retryable {
  retry(): boolean;
}
