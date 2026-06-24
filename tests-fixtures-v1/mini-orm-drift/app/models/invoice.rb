class Invoice < ApplicationRecord
  # ORM model declares these attributes/validations:
  validates :total, presence: true            # expects decimal column `total`
  validates :customer_email, presence: true   # expects column `customer_email`  <-- NOT in live schema
  enum status: { draft: 0, sent: 1, paid: 2 }  # expects integer column `status`
  attribute :discount_rate, :decimal          # model says decimal; live schema is integer  <-- type drift
  # workaround: `total` is stored at higher precision in the DB than the model assumes (see schema)
end
