# Live database schema (as reflected from the running DB via an R7-approved read).
# Dialect: this app runs on a backend that reports numeric/tinyint type names.
ActiveRecord::Schema.define(version: 2026_06_01) do
  create_table "subscriptions", force: :cascade do |t|
    t.bigint   "plan_id",    null: false
    t.bigint   "account_id", null: false

    # SEED 2: live column is numeric(12,4); model assumes decimal(10,2).
    # Same base type (numeric == decimal) but precision/scale DIFFER -> precision drift, STILL fires.
    t.numeric  "monthly_amount", precision: 12, scale: 4, null: false

    # SEED 3a: live numeric(8,2); model decimal(8,2). Synonym + IDENTICAL params -> MUST NOT fire.
    t.numeric  "proration_credit", precision: 8, scale: 2

    # SEED 3b: live tinyint(1); model :boolean. tinyint(1) is the boolean synonym -> MUST NOT fire.
    t.tinyint  "auto_renew", limit: 1, default: 1

    # SEED 1: model validates `external_billing_id` presence, but NO such column exists here.
    # MODEL-ONLY FIELD -> IF-2 High.

    t.integer  "status", default: 0
    t.datetime "current_period_end"
    t.datetime "created_at"
    t.datetime "updated_at"
  end

  create_table "plans", force: :cascade do |t|
    t.string   "name", null: false
    t.integer  "interval_days", null: false
    # `price` numeric(12,4) matches the model's decimal(12,4) -> no drift.
    t.numeric  "price", precision: 12, scale: 4
    t.datetime "created_at"
    t.datetime "updated_at"
  end
end
