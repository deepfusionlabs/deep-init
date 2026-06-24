class InvoicesController < ApplicationController
  active_scaffold :invoice
  before_action :require_login
  before_action :require_invoice_permission, only: [:create, :update, :mark_paid]

  # WF: Create invoice — auth required → validate role → create draft → add line items
  def create
    @invoice = current_user.invoices.build(invoice_params)
    @invoice.status = 'draft'
    if @invoice.save
      redirect_to @invoice, notice: 'Invoice created'
    else
      render :new
    end
  end

  # WF: Mark invoice paid — verify not cancelled → update status → record payment date
  def mark_paid
    @invoice = Invoice.find(params[:id])
    @invoice.mark_paid!
    redirect_to @invoice, notice: 'Invoice marked as paid'
  rescue => e
    redirect_to @invoice, alert: e.message
  end

  # IP: Stripe integration for payment processing
  def send_reminder
    @invoice = Invoice.find(params[:id])
    InvoiceMailer.reminder(@invoice).deliver_later
    redirect_to @invoice, notice: 'Reminder sent'
  end

  private

  # BR: Only admin and accountant roles can create/modify invoices
  def require_invoice_permission
    unless current_user.can_create_invoices?
      redirect_to invoices_path, alert: 'Not authorized'
    end
  end

  def invoice_params
    params.require(:invoice).permit(:due_date, :notes, line_items_attributes: [:description, :amount])
  end
end
