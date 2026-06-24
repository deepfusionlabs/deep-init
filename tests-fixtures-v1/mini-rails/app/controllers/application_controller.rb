class ApplicationController < ActionController::Base
  helper_method :current_user, :logged_in?

  private

  def current_user
    @current_user ||= User.find_by(id: session[:user_id])
  end

  def logged_in?
    current_user.present?
  end

  # BR: Authentication required for all controllers except sessions
  def require_login
    unless logged_in?
      redirect_to new_session_path, alert: 'Please log in'
    end
  end
end
