class InvoiceService
  # Decided to use service objects over fat models for complex operations
  # This keeps the Invoice model focused on data and validation

  # WF: Check overdue invoices — find sent invoices past due → mark overdue → notify
  def self.check_overdue
    Invoice.overdue.find_each do |invoice|
      invoice.update!(status: 'overdue')
      InvoiceMailer.overdue_notice(invoice).deliver_later
    end
  end

  # IP: Stripe API for payment link generation
  def self.generate_payment_link(invoice)
    Stripe::PaymentLink.create(
      line_items: [{ price: create_stripe_price(invoice.total), quantity: 1 }],
      metadata: { invoice_id: invoice.id, invoice_number: invoice.invoice_number }
    )
  end

  private

  def self.create_stripe_price(amount)
    Stripe::Price.create(unit_amount: (amount * 100).to_i, currency: 'usd', product_data: { name: 'Invoice Payment' })
  end
end
