class LineItem < ApplicationRecord
  belongs_to :invoice

  # BR: Line item amount must be positive
  validates :amount, numericality: { greater_than: 0 }
  validates :description, presence: true
end
