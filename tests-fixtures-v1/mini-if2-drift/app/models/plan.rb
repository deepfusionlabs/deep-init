class Plan < ApplicationRecord
  has_many :subscriptions

  # `price` is decimal(12,4) in both the model and the live schema -> no drift.
  attribute :price, :decimal, precision: 12, scale: 4

  validates :name, presence: true
  validates :interval_days, presence: true, numericality: { greater_than: 0 }
end
