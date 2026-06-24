// AuditRepository does NOT extend BaseRepository — the lone deviant among 5
// repositories (the IF-4 fire ADR-100 governs; the census corroborates it as a
// minority outlier: 4 of 5 siblings conform).
export class AuditRepository {
  private rows: unknown[] = [];

  append(entry: unknown) {
    this.rows.push(entry);
  }
}
