from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Checkout
    path('checkout/<int:plan_id>/', views.checkout, name='checkout'),
    path('demo-upgrade/<int:plan_id>/', views.demo_upgrade, name='demo_upgrade'),
    path('success/', views.success, name='success'),
    path('cancel/', views.cancel, name='cancel'),
    
    # Subscription management
    path('subscription/', views.subscription_management, name='subscription_management'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/reactivate/', views.reactivate_subscription, name='reactivate_subscription'),
    
    # Payment history
    path('history/', views.payment_history, name='payment_history'),
    
    # Webhooks
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]
