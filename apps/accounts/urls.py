from django.urls import path
from django.contrib.auth import views as auth_views
from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    # Use our custom login view instead of the Django one
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/email-preferences/', views.update_email_preferences, name='update_email_preferences'),
    path('delete-profile/', views.delete_profile_confirm, name='delete_profile_confirm'),
    path('delete-profile/execute/', views.delete_profile_execute, name='delete_profile_execute'),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('accepted-policy/', views.view_accepted_policy, name='accepted_policy'),

    
]