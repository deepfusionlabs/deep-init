class User < ApplicationRecord
  acts_as_authentic do |c|
    c.crypto_provider = Authlogic::CryptoProviders::BCrypt
    c.minimum_password_length = 8
  end

  has_many :invoices, foreign_key: :created_by_id
  has_many :reports

  # BR: Email must be unique and valid format
  validates :email, presence: true, uniqueness: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  # BR: Role must be one of: admin, accountant, viewer
  validates :role, inclusion: { in: %w[admin accountant viewer] }

  def admin?
    role == 'admin'
  end

  def can_create_invoices?
    role.in?(%w[admin accountant])
  end
end
