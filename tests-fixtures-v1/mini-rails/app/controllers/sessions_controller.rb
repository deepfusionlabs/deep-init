class SessionsController < ApplicationController
  # WF: Login — find user by email → verify password (Authlogic) → create session
  def create
    user = User.find_by(email: params[:email])
    if user&.valid_password?(params[:password])
      session[:user_id] = user.id
      redirect_to dashboard_path, notice: 'Logged in'
    else
      flash.now[:alert] = 'Invalid email or password'
      render :new
    end
  end

  def destroy
    session[:user_id] = nil
    redirect_to root_path
  end
end
