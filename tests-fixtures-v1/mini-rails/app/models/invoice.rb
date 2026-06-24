class Invoice < ApplicationRecord
  belongs_to :creator, class_name: 'User', foreign_key: :created_by_id
  has_many :line_items, dependent: :destroy

  # BR: Invoice total = sum of line item amounts
  # BR: Invoice number auto-generated with prefix INV-YYYY-NNNN
  # BR: Invoice status transitions: draft → sent → paid (or → overdue)
  # BR: Overdue if unpaid and past due_date
  validates :status, inclusion: { in: %w[draft sent paid overdue cancelled] }
  validates :invoice_number, uniqueness: true
  before_create :generate_invoice_number

  scope :overdue, -> { where(status: 'sent').where('due_date < ?', Date.today) }

  def mark_paid!
    raise 'Cannot pay a cancelled invoice' if status == 'cancelled'
    update!(status: 'paid', paid_at: Time.current)
  end

  def total
    line_items.sum(:amount)
  end

  private

  def generate_invoice_number
    year = Date.today.year
    seq = Invoice.where('invoice_number LIKE ?', "INV-#{year}-%").count + 1
    self.invoice_number = "INV-#{year}-#{seq.to_s.rjust(4, '0')}"
  end
end
