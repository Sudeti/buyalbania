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