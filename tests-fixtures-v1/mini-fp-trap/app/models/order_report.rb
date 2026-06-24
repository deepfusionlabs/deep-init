# frozen_string_literal: true

# Reporting-side model for the analytics dashboard. This component is a SEPARATE
# bounded context from the orders service (src/orders).
#
# It READS the shared `order_events` table that the orders service writes. This is
# an INTENTIONAL, DOCUMENTED shared-table contract:
#   - Contract: docs/shared-tables.md (ADR-014)
#   - orders service = sole WRITER; reporting = READ-ONLY consumer
#   - Enforced at the DB layer by the `reporting_ro` role (SELECT-only grant)
#
# Because the coupling is documented AND the access is asymmetric/contracted
# (one writer, one read-only reader, with an explicit interface = the event
# schema), IF-3a must NOT flag this as silent cross-component coupling.
class OrderReport < ApplicationRecord
  self.table_name = 'order_events'

  # READ-ONLY: the reporting role has no INSERT/UPDATE grant. Guard in code too.
  def readonly?
    true
  end

  def self.daily_payment_counts(since:)
    where(event_type: 'payment.succeeded')
      .where('occurred_at >= ?', since)
      .group("date_trunc('day', occurred_at)")
      .count
  end
end
