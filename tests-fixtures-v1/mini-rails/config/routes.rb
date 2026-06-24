Rails.application.routes.draw do
  resources :sessions, only: [:new, :create, :destroy]
  resources :users, only: [:new, :create, :show, :edit, :update]
  resources :invoices do
    member do
      post :mark_paid
      post :send_reminder
    end
  end
  resources :reports, only: [:index, :show, :create]
  get 'dashboard', to: 'reports#dashboard'
  root 'sessions#new'
end
