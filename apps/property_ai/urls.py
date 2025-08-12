# Updated urls.py
from django.urls import path
from . import views

app_name = 'property_ai'

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    path('analyze/', views.analyze_property, name='analyze_property'),
    path('analysis/<uuid:analysis_id>/', views.analysis_detail, name='analysis_detail'),
    
    # User pages
    path('my-analyses/', views.my_analyses, name='my_analyses'),
    
    # Market insights
    path('market/', views.market_overview, name='market_overview'),
    path('api/market-analytics/', views.market_analytics_api, name='market_analytics_api'),
    
    path('download-report/<uuid:analysis_id>/', views.download_report, name='download_report'),
    
    # API endpoints (optional for future)
    # path('api/quick-analysis/', views.quick_analysis_api, name='quick_analysis_api'),
    # path('api/comparable-properties/', views.comparable_properties_api, name='comparable_properties_api'),
]