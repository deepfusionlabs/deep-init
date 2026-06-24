class Report < ApplicationRecord
  belongs_to :user

  # BR: Report types: revenue, aging, outstanding
  validates :report_type, inclusion: { in: %w[revenue aging outstanding] }

  def generate_data
    case report_type
    when 'revenue'
      Invoice.where(status: 'paid').group_by_month(:paid_at).sum(:total)
    when 'aging'
      Invoice.overdue.order(:due_date)
    when 'outstanding'
      Invoice.where(status: 'sent').order(:due_date)
    end
  end
end
