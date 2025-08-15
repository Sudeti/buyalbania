# Updated urls.py
from django.urls import path
from apps.property_ai.views import analysis_views, home_views, report_views, analytics_views

app_name = 'property_ai'

urlpatterns = [
    # Main pages
    path('', home_views.home, name='home'),
    path('analyze/', analysis_views.analyze_property, name='analyze_property'),
    path('analysis/<uuid:analysis_id>/', analysis_views.analysis_detail, name='analysis_detail'),
    
    # User pages
    path('my-analyses/', analysis_views.my_analyses, name='my_analyses'),
    path('analytics/', analytics_views.analytics_dashboard, name='analytics_dashboard'),
    
    # API endpoints
    path('api/market-insights/', analytics_views.market_insights_api, name='market_insights_api'),
    path('api/opportunity-analysis/<uuid:analysis_id>/', analytics_views.opportunity_analysis_api, name='opportunity_analysis_api'),
    
    path('download-report/<uuid:analysis_id>/', report_views.download_report, name='download_report'),
]