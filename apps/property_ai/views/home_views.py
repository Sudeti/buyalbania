# Updated views.py - Sale properties workflow
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from ..models import PropertyAnalysis
import logging

logger = logging.getLogger(__name__)

def home(request):
    """Property analysis home page with sale focus"""
    # Get some stats for the homepage
    total_analyses = PropertyAnalysis.objects.filter(status='completed').count()
    avg_score = PropertyAnalysis.objects.filter(
        status='completed', 
        investment_score__isnull=False
    ).aggregate(avg_score=Avg('investment_score'))['avg_score']
    
    # Recent high-scoring properties
    featured_properties = PropertyAnalysis.objects.filter(
        status='completed',
        investment_score__gte=75
    ).order_by('-investment_score')[:3]
    
    # Get subscription plans for pricing display
    from apps.payments.models import SubscriptionPlan
    subscription_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
    
    context = {
        'features': [
            'AI-powered investment analysis for sale properties',
            'Albanian real estate market insights',
            'Rental yield calculations',
            'Risk assessment & ROI projections',
            'Instant property evaluation',
            'Investment recommendations'
        ],
        'stats': {
            'total_analyses': total_analyses,
            'avg_score': round(avg_score or 0, 1),
        },
        'featured_properties': featured_properties,
        'subscription_plans': subscription_plans,
    }
    return render(request, 'property_ai/home.html', context)

def services(request):
    """Services and pricing page"""
    # Get some stats for social proof
    total_analyses = PropertyAnalysis.objects.filter(status='completed').count()
    
        # Get subscription plans from database
    from apps.payments.models import SubscriptionPlan
    subscription_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
    
    # Define the pricing tiers and features - SIMPLIFIED with higher prices
    tiers = [
        {
            'name': 'Free',
            'price': '€0',
            'period': 'month',
            'analyses': '1 analysis',
            'period_text': 'per month',
            'color': 'warning',
            'popular': False,
            'features': [
                '1 property analysis per month',
                'AI investment score',
                'PDF report via email',
                'Access to existing analyses',
                'No market insights',
            ],
            'cta_text': 'Start Free',
            'cta_url': 'property_ai:analyze_property',
            'cta_class': 'btn-warning'
        }
    ]
    
    # Add paid plans from database
    for plan in subscription_plans:
        if plan.tier == 'basic':
            tiers.append({
                'name': plan.name,
                'price': f'€{plan.price_monthly}',
                'period': 'month',
                'analyses': f'{plan.analyses_per_month} analyses' if plan.analyses_per_month > 0 else 'Unlimited',
                'period_text': 'per month',
                'color': 'primary',
                'popular': True,
                'features': plan.features,
                'cta_text': 'Upgrade to Basic',
                'cta_url': 'payments:checkout',
                'cta_class': 'btn-primary',
                'plan_id': plan.id
            })
        elif plan.tier == 'premium':
            tiers.append({
                'name': plan.name,
                'price': f'€{plan.price_monthly}',
                'period': 'month',
                'analyses': 'Unlimited',
                'period_text': 'analyses',
                'color': 'success',
                'popular': False,
                'features': plan.features,
                'cta_text': 'Go Premium',
                'cta_url': 'payments:checkout',
                'cta_class': 'btn-success',
                'plan_id': plan.id
            })
    
    context = {
        'tiers': tiers,
        'stats': {
            'total_analyses': total_analyses,
        }
    }
    return render(request, 'property_ai/services.html', context)