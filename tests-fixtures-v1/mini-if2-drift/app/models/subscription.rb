class Subscription < ApplicationRecord
  # Billing subscription. ORM declares the attributes/validations below.
  belongs_to :plan
  belongs_to :account

  # --- SEED 2: precision/scale drift (base-type synonym, params DIFFER) ---------------
  # Model assumes decimal(10,2); live schema stores numeric(12,4).
  # `decimal` and `numeric` are dialect synonyms of the SAME base type, BUT the
  # precision/scale differ, so the base-type-equivalence layer must STILL flag this.
  attribute :monthly_amount, :decimal, precision: 10, scale: 2

  # --- SEED 3a: dialect synonym with IDENTICAL params (MUST NOT fire) ------------------
  # Model says decimal(8,2); live schema says numeric(8,2). Same base type, same
  # precision/scale -> suppressed by type-equivalence (decimal == numeric here).
  attribute :proration_credit, :decimal, precision: 8, scale: 2

  # --- SEED 3b: dialect synonym tinyint(1) == boolean (MUST NOT fire) ------------------
  # Model declares :boolean; live schema column is the MySQL idiom tinyint(1).
  # tinyint(1) is the boolean synonym -> suppressed by type-equivalence.
  attribute :auto_renew, :boolean, default: true

  validates :monthly_amount, presence: true
  validates :external_billing_id, presence: true   # expects column `external_billing_id`

  enum status: { trialing: 0, active: 1, past_due: 2, canceled: 3 }

  def renew!
    update!(current_period_end: current_period_end + plan.interval_days.days)
  end
end
