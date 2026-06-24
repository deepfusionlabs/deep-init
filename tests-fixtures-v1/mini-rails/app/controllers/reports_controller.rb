class ReportsController < ApplicationController
  before_action :require_login

  def index
    @reports = current_user.reports.order(created_at: :desc)
  end

  def show
    @report = Report.find(params[:id])
    # BR: Users can only view their own reports (unless admin)
    unless @report.user == current_user || current_user.admin?
      redirect_to reports_path, alert: 'Not authorized'
    end
  end

  def dashboard
    @revenue = Invoice.where(status: 'paid').sum(:total)
    @outstanding = Invoice.where(status: 'sent').count
    @overdue = Invoice.overdue.count
  end

  def create
    @report = current_user.reports.build(report_type: params[:report_type])
    @report.save!
    redirect_to @report
  end
end
