# apps/core/admin.py
from django.contrib import admin
from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'maintenance_mode', 'max_free_usages', 'premium_price')
    
    def has_add_permission(self, request):
        # Only allow one instance of site settings
        return SiteSettings.objects.count() == 0