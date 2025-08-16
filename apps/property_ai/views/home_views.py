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
    }
    return render(request, 'property_ai/home.html', context)

def services(request):
    """Services and pricing page"""
    # Get some stats for social proof
    total_analyses = PropertyAnalysis.objects.filter(status='completed').count()
    
    # Define the pricing tiers and features
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
                'Basic investment score',
                'Market positioning insights',
                'Access to existing analyses',
                'Email support',
            ],
            'cta_text': 'Start Free',
            'cta_url': 'property_ai:analyze_property',
            'cta_class': 'btn-warning'
        },
        {
            'name': 'Basic',
            'price': '€5',
            'period': 'month',
            'analyses': '10 analyses',
            'period_text': 'per month',
            'color': 'primary',
            'popular': True,
            'features': [
                '10 property analyses per month',
                'Enhanced investment scoring',
                'Detailed market analytics',
                'Negotiation leverage insights',
                'Price positioning analysis',
                'Access to all existing analyses',
                'Priority email support',
                'Property deal alerts',
            ],
            'cta_text': 'Upgrade to Basic',
            'cta_url': '#upgrade-basic',
            'cta_class': 'btn-primary'
        },
        {
            'name': 'Premium',
            'price': '€15',
            'period': 'month',
            'analyses': 'Unlimited',
            'period_text': 'analyses',
            'color': 'success',
            'popular': False,
            'features': [
                'Unlimited property analyses',
                'Advanced AI insights',
                'Comprehensive market reports',
                'Portfolio analytics dashboard',
                'Custom investment criteria',
                'Priority customer support',
                'Advanced property alerts',
                'Market trend analysis',
                'ROI projections',
                'Risk assessment reports',
            ],
            'cta_text': 'Go Premium',
            'cta_url': '#upgrade-premium',
            'cta_class': 'btn-success'
        }
    ]
    
    context = {
        'tiers': tiers,
        'stats': {
            'total_analyses': total_analyses,
        }
    }
    return render(request, 'property_ai/services.html', context)