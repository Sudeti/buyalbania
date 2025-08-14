# Updated urls.py
from django.urls import path
from apps.property_ai.views import analysis_views, home_views, market_views, report_views

app_name = 'property_ai'

urlpatterns = [
    # Main pages
    path('', home_views.home, name='home'),
    path('analyze/', analysis_views.analyze_property, name='analyze_property'),
    path('analysis/<uuid:analysis_id>/', analysis_views.analysis_detail, name='analysis_detail'),
    
    # User pages
    path('my-analyses/', analysis_views.my_analyses, name='my_analyses'),
    
    # Market insights
    path('market/', market_views.market_overview, name='market_overview'),
    path('api/market-analytics/', market_views.market_analytics_api, name='market_analytics_api'),
    
    path('download-report/<uuid:analysis_id>/', report_views.download_report, name='download_report'),
    
    # API endpoints (optional for future)
    # path('api/quick-analysis/', views.quick_analysis_api, name='quick_analysis_api'),
    # path('api/comparable-properties/', views.comparable_properties_api, name='comparable_properties_api'),
]