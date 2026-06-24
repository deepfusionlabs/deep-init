import { LegacyService } from "../core/base";

// ReportService is the LONE service still extending LegacyService — the only
// site that conforms to ADR-101. Because the documented rule is contradicted by
// the MAJORITY of its class (5 of 6 migrated to BaseService), the census marks
// ADR-101 as de-facto STALE and down-ranks any IF-4 fire raised against it.
export class ReportService extends LegacyService {
  build(range: string) {
    return this.run("report.build", range);
  }
}
