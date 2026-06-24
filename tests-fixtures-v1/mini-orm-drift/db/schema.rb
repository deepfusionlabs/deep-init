# Live database schema (as reflected from the running DB).
ActiveRecord::Schema.define(version: 2026_05_01) do
  create_table "invoices", force: :cascade do |t|
    t.decimal  "total", precision: 12, scale: 4   # model assumes (10,2) — precision drift
    t.integer  "status", default: 0
    t.integer  "discount_rate"                     # model declares :decimal — TYPE DRIFT
    # NOTE: no `customer_email` column — model declares it (MODEL-ONLY FIELD)
    t.datetime "created_at"
    t.datetime "updated_at"
  end
  create_table "audit_logs", force: :cascade do |t|  # ORPHAN: no ActiveRecord model references it
    t.string   "action"
    t.datetime "created_at"
  end
end
