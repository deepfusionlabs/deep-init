# ActiveRecord schema dump for the reporting-side MySQL replica.
# The reporting model maps a `flagged` column declared as tinyint(1) in MySQL to a
# Ruby boolean. tinyint(1) === boolean in MySQL (Rails maps it as :boolean), and
# there are no extra params to compare. IF-2 must NOT flag this as a type mismatch.

ActiveRecord::Schema.define(version: 2025_11_02_000001) do
  create_table "order_events", force: :cascade do |t|
    t.bigint   "order_id",   null: false
    t.string   "event_type", limit: 64, null: false
    # tinyint(1) in MySQL DDL; Rails reads it as :boolean. Synonym pair, identical.
    t.boolean  "flagged",    default: false, null: false
    t.datetime "occurred_at", null: false
  end
end
