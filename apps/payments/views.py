import stripe
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from .models import SubscriptionPlan, Customer, Subscription, Payment, PaymentMethod
from apps.accounts.models import UserProfile
import json

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def checkout(request, plan_id):
    """Create checkout session for subscription"""
    try:
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
        
        # Check if Stripe is properly configured
        if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith('sk_test_'):
            # Stripe not configured - show demo mode
            return render(request, 'payments/demo_upgrade.html', {
                'plan': plan,
                'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY
            })
        
        # Get or create Stripe customer
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            defaults={'stripe_customer_id': None}
        )
        
        if not customer.stripe_customer_id:
            # Create Stripe customer
            stripe_customer = stripe.Customer.create(
                email=request.user.email,
                name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                metadata={'user_id': request.user.id}
            )
            customer.stripe_customer_id = stripe_customer.id
            customer.save()
        
        # Check if plan has Stripe price ID
        if not plan.stripe_price_id_monthly:
            messages.error(request, 'Payment plan not properly configured. Please contact support.')
            return redirect('property_ai:services')
        
        # Show checkout page with Stripe Elements
        return render(request, 'payments/checkout.html', {
            'plan': plan,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY
        })
        
    except Exception as e:
        logger.error(f"Error in checkout: {e}")
        return render(request, 'payments/error.html', {
            'error_message': str(e),
            'plan_id': plan_id
        })

@login_required
def success(request):
    """Handle successful payment"""
    session_id = request.GET.get('session_id')
    
    if not session_id:
        messages.error(request, 'Invalid session.')
        return redirect('property_ai:services')
    
    try:
        # Retrieve the checkout session
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            # Update user profile
            profile = request.user.profile
            plan_tier = session.metadata.get('plan_tier', 'basic')
            profile.subscription_tier = plan_tier
            profile.save()
            
            # Get plan details for template
            plan = SubscriptionPlan.objects.get(tier=plan_tier)
            
            return render(request, 'payments/success.html', {
                'plan_name': plan.name,
                'analyses_count': plan.analyses_per_month,
                'next_billing_date': (timezone.now() + timezone.timedelta(days=30)).strftime('%B %d, %Y')
            })
        else:
            messages.warning(request, 'Payment is being processed. You will receive an email confirmation shortly.')
            return redirect('accounts:user_profile')
        
    except Exception as e:
        logger.error(f"Error processing success: {e}")
        return render(request, 'payments/error.html', {
            'error_message': 'Error processing payment. Please contact support.',
            'plan_id': None
        })

@login_required
def cancel(request):
    """Handle cancelled payment"""
    profile = request.user.profile
    return render(request, 'payments/cancel.html', {
        'current_tier': profile.subscription_tier,
        'remaining_analyses': profile.remaining_analyses
    })

@login_required
def demo_upgrade(request, plan_id):
    """Demo upgrade when Stripe is not configured"""
    try:
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
        
        if request.method == 'POST':
            # For demo purposes, directly upgrade the user
            profile = request.user.profile
            profile.subscription_tier = plan.tier
            profile.save()
            
            # Create a demo subscription record
            customer, created = Customer.objects.get_or_create(
                user=request.user,
                defaults={'stripe_customer_id': f'demo_customer_{request.user.id}'}
            )
            
            subscription = Subscription.objects.create(
                user=request.user,
                customer=customer,
                plan=plan,
                stripe_subscription_id=f'demo_sub_{request.user.id}_{plan.tier}',
                current_period_start=timezone.now(),
                current_period_end=timezone.now() + timezone.timedelta(days=30),
                status='active'
            )
            
            messages.success(request, f'Demo upgrade successful! You now have {plan.name} access.')
            return redirect('accounts:user_profile')
        
        # Show demo upgrade page
        return render(request, 'payments/demo_upgrade.html', {
            'plan': plan
        })
        
    except Exception as e:
        logger.error(f"Error in demo upgrade: {e}")
        return render(request, 'payments/error.html', {
            'error_message': 'Error processing demo upgrade. Please try again.',
            'plan_id': plan_id
        })

@login_required
def subscription_management(request):
    """Manage subscription"""
    try:
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            defaults={'stripe_customer_id': None}
        )
        
        # Get active subscription
        active_subscription = Subscription.objects.filter(
            customer=customer,
            status__in=['active', 'trialing']
        ).first()
        
        # Get available plans
        plans = SubscriptionPlan.objects.filter(is_active=True)
        
        context = {
            'active_subscription': active_subscription,
            'plans': plans,
            'customer': customer,
        }
        
        return render(request, 'payments/subscription_management.html', context)
        
    except Exception as e:
        logger.error(f"Error in subscription management: {e}")
        messages.error(request, 'Error loading subscription management.')
        return redirect('accounts:user_profile')

@login_required
def cancel_subscription(request):
    """Cancel subscription"""
    try:
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            defaults={'stripe_customer_id': None}
        )
        
        subscription = Subscription.objects.filter(
            customer=customer,
            status__in=['active', 'trialing']
        ).first()
        
        if not subscription:
            messages.error(request, 'No active subscription found.')
            return redirect('payments:subscription_management')
        
        # Check if this is a demo subscription
        if subscription.stripe_subscription_id.startswith('demo_sub_'):
            # Demo subscription - just update local record
            subscription.cancel_at_period_end = True
            subscription.canceled_at = timezone.now()
            subscription.save()
            
            messages.success(request, 'Demo subscription cancelled successfully.')
        else:
            # Live Stripe subscription
            try:
                # Cancel in Stripe
                stripe_subscription = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                
                # Update local subscription
                subscription.cancel_at_period_end = True
                subscription.canceled_at = timezone.now()
                subscription.save()
                
                messages.success(request, 'Subscription will be cancelled at the end of the current billing period.')
            except Exception as stripe_error:
                logger.error(f"Stripe error cancelling subscription: {stripe_error}")
                messages.error(request, 'Error cancelling subscription in Stripe. Please try again.')
        
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        messages.error(request, 'Error cancelling subscription. Please try again.')
    
    return redirect('payments:subscription_management')

@login_required
def reactivate_subscription(request):
    """Reactivate cancelled subscription"""
    try:
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            defaults={'stripe_customer_id': None}
        )
        
        subscription = Subscription.objects.filter(
            customer=customer,
            status__in=['active', 'trialing']
        ).first()
        
        if not subscription or not subscription.cancel_at_period_end:
            messages.error(request, 'No cancelled subscription found.')
            return redirect('payments:subscription_management')
        
        # Check if this is a demo subscription
        if subscription.stripe_subscription_id.startswith('demo_sub_'):
            # Demo subscription - just update local record
            subscription.cancel_at_period_end = False
            subscription.canceled_at = None
            subscription.save()
            
            messages.success(request, 'Demo subscription reactivated successfully.')
        else:
            # Live Stripe subscription
            try:
                # Reactivate in Stripe
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=False
                )
                
                # Update local subscription
                subscription.cancel_at_period_end = False
                subscription.canceled_at = None
                subscription.save()
                
                messages.success(request, 'Subscription reactivated successfully.')
            except Exception as stripe_error:
                logger.error(f"Stripe error reactivating subscription: {stripe_error}")
                messages.error(request, 'Error reactivating subscription in Stripe. Please try again.')
        
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        messages.error(request, 'Error reactivating subscription. Please try again.')
    
    return redirect('payments:subscription_management')

@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        handle_checkout_session_completed(event['data']['object'])
    elif event['type'] == 'invoice.payment_succeeded':
        handle_invoice_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_invoice_payment_failed(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    
    return HttpResponse(status=200)

def handle_checkout_session_completed(session):
    """Handle successful checkout"""
    try:
        user_id = session.metadata.get('user_id')
        plan_tier = session.metadata.get('plan_tier')
        
        if user_id and plan_tier:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Get or create customer
            customer, created = Customer.objects.get_or_create(
                user=user,
                defaults={'stripe_customer_id': session.customer}
            )
            
            if not customer.stripe_customer_id:
                customer.stripe_customer_id = session.customer
                customer.save()
            
            # Get subscription plan
            plan = SubscriptionPlan.objects.get(tier=plan_tier)
            
            # Create subscription record
            subscription = Subscription.objects.create(
                user=user,
                customer=customer,
                plan=plan,
                stripe_subscription_id=session.subscription,
                current_period_start=timezone.datetime.fromtimestamp(
                    session.subscription_data.current_period_start, tz=timezone.utc
                ),
                current_period_end=timezone.datetime.fromtimestamp(
                    session.subscription_data.current_period_end, tz=timezone.utc
                ),
                status='active'
            )
            
            # Update user profile
            profile = user.profile
            profile.subscription_tier = plan_tier
            profile.save()
            
            logger.info(f"User {user.email} upgraded to {plan_tier} plan with subscription {subscription.id}")
            
    except Exception as e:
        logger.error(f"Error handling checkout session completed: {e}")

def handle_invoice_payment_succeeded(invoice):
    """Handle successful payment"""
    try:
        subscription_id = invoice.subscription
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        
        # Create payment record
        Payment.objects.create(
            user=subscription.user,
            subscription=subscription,
            stripe_payment_intent_id=invoice.payment_intent,
            amount=invoice.amount_paid / 100,  # Convert from cents
            currency=invoice.currency,
            status='succeeded',
            description=f"Payment for {subscription.plan.name}",
            metadata={'invoice_id': invoice.id}
        )
        
        logger.info(f"Payment succeeded for user {subscription.user.email}")
        
    except Exception as e:
        logger.error(f"Error handling invoice payment succeeded: {e}")

def handle_invoice_payment_failed(invoice):
    """Handle failed payment"""
    try:
        subscription_id = invoice.subscription
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        
        # Update subscription status
        subscription.status = 'past_due'
        subscription.save()
        
        logger.warning(f"Payment failed for user {subscription.user.email}")
        
    except Exception as e:
        logger.error(f"Error handling invoice payment failed: {e}")

def handle_subscription_updated(subscription_data):
    """Handle subscription updates"""
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_data.id)
        
        # Update subscription data
        subscription.status = subscription_data.status
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            subscription_data.current_period_start, tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            subscription_data.current_period_end, tz=timezone.utc
        )
        subscription.cancel_at_period_end = subscription_data.cancel_at_period_end
        
        if subscription_data.canceled_at:
            subscription.canceled_at = timezone.datetime.fromtimestamp(
                subscription_data.canceled_at, tz=timezone.utc
            )
        
        subscription.save()
        
        logger.info(f"Subscription updated for user {subscription.user.email}")
        
    except Exception as e:
        logger.error(f"Error handling subscription updated: {e}")

def handle_subscription_deleted(subscription_data):
    """Handle subscription deletion"""
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_data.id)
        
        # Update subscription status
        subscription.status = 'canceled'
        subscription.save()
        
        # Update user profile to free tier
        profile = subscription.user.profile
        profile.subscription_tier = 'free'
        profile.save()
        
        logger.info(f"Subscription cancelled for user {subscription.user.email}")
        
    except Exception as e:
        logger.error(f"Error handling subscription deleted: {e}")

@login_required
def payment_history(request):
    """View payment history"""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'payments': payments,
    }
    
    return render(request, 'payments/payment_history.html', context)
