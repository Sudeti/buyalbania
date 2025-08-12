"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.contrib.auth import views as auth_views
from apps.property_ai import views as property_views


urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),  # <-- use the new accounts app
    path('', include('apps.property_ai.urls')),  # <-- use the new property_ai app
    path('social-auth/', include('social_django.urls', namespace='social')),
    
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

