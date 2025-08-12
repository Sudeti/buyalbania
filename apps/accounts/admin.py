from django.contrib import admin
from .models import UserProfile, PrivacyPolicyVersion, PrivacyPolicyConsent, PageView

# Register your models here.

admin.site.register(UserProfile)

@admin.register(PrivacyPolicyVersion)
class PrivacyPolicyVersionAdmin(admin.ModelAdmin):
    list_display = ('version', 'effective_date', 'is_active', 'created_at')
    list_filter = ('is_active', 'effective_date')
    search_fields = ('version', 'content')
    readonly_fields = ('created_at',)
    
    def save_model(self, request, obj, form, change):
        # If setting this version as active, deactivate all others
        if obj.is_active:
            PrivacyPolicyVersion.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)

@admin.register(PrivacyPolicyConsent)
class PrivacyPolicyConsentAdmin(admin.ModelAdmin):
    list_display = ('user', 'policy_version', 'accepted_at', 'ip_address')
    list_filter = ('policy_version', 'accepted_at')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('user', 'policy_version', 'accepted_at', 'ip_address', 'user_agent')
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation of consent records
    
@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ['page_name', 'user', 'ip_address', 'timestamp']
    list_filter = ['page_name', 'timestamp']
    search_fields = ['page_name', 'user__username', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'