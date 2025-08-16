from django.contrib import admin
from .models import SubscriptionPlan, Customer, Subscription, Payment, PaymentMethod

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'price_monthly', 'analyses_per_month', 'is_active']
    list_filter = ['tier', 'is_active']
    search_fields = ['name', 'tier']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['user', 'stripe_customer_id', 'created_at']
    search_fields = ['user__email', 'user__username', 'stripe_customer_id']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'current_period_end', 'cancel_at_period_end']
    list_filter = ['status', 'plan', 'cancel_at_period_end']
    search_fields = ['user__email', 'stripe_subscription_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['user__email', 'stripe_payment_intent_id', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'brand', 'last4', 'is_default']
    list_filter = ['type', 'brand', 'is_default']
    search_fields = ['user__email', 'stripe_payment_method_id']
    readonly_fields = ['created_at']
