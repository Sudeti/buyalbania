from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email_verification_token = models.CharField(max_length=64, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    subscription_tier = models.CharField(max_length=20, choices=[
        ('free', 'Free'),
        ('basic', 'Basic - €5/month'),
        ('premium', 'Premium - €15/month'),
    ], default='free')
    
    # Free user quota tracking
    monthly_analyses_used = models.IntegerField(default=0)
    monthly_quota_reset_date = models.DateField(null=True, blank=True)
    
    # NEW: Email notification preferences
    email_property_alerts = models.BooleanField(
        default=True, 
        help_text="Receive emails about new properties that are good deals"
    )
    preferred_locations = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of preferred locations for property alerts (e.g., ['Tirana', 'Durrës'])"
    )
    min_investment_score = models.IntegerField(
        default=70,
        help_text="Minimum investment score for properties to include in alerts"
    )
    max_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum price for properties to include in alerts"
    )
    
    def reset_monthly_quota_if_needed(self):
        """Reset quota on first of each month"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.monthly_quota_reset_date or today.month != self.monthly_quota_reset_date.month:
            self.monthly_analyses_used = 0
            self.monthly_quota_reset_date = today
            self.save()
    
    def can_analyze_property(self):
        """Check if user can analyze a new property"""
        self.reset_monthly_quota_if_needed()
        
        if self.subscription_tier == 'free':
            return self.monthly_analyses_used < 1  # 1 per month
        elif self.subscription_tier == 'basic':
            return self.monthly_analyses_used < 10  # 10 per month
        else:  # premium
            return True  # unlimited
    
    def use_analysis_quota(self):
        """Consume one analysis from quota"""
        self.reset_monthly_quota_if_needed()
        if self.can_analyze_property():
            self.monthly_analyses_used += 1
            self.save()
            return True
        return False
    
    @property
    def remaining_analyses(self):
        """How many analyses left this month"""
        self.reset_monthly_quota_if_needed()
        if self.subscription_tier == 'free':
            return max(0, 1 - self.monthly_analyses_used)
        elif self.subscription_tier == 'basic':
            return max(0, 10 - self.monthly_analyses_used)
        else:
            return float('inf')  # unlimited
    
    def should_receive_property_alert(self, property_analysis):
        """Check if user should receive alert for this property"""
        if not self.email_property_alerts:
            return False
            
        # Check if property matches user's preferences
        if self.preferred_locations:
            location_match = any(
                location.lower() in property_analysis.property_location.lower() 
                for location in self.preferred_locations
            )
            if not location_match:
                return False
        
        # Check max price (investment score not available for new properties)
        if self.max_price and property_analysis.asking_price > self.max_price:
            return False
            
        return True
        
class PageView(models.Model):
    """Track page views for analytics"""
    page_name = models.CharField(max_length=100)
    url_path = models.CharField(max_length=500)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=40, blank=True)
    
    class Meta:
        verbose_name = "Page View"
        verbose_name_plural = "Page Views"
        indexes = [
            models.Index(fields=['page_name', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.page_name} - {self.timestamp}"
    
class PrivacyPolicyVersion(models.Model):
    """Stores versions of the privacy policy for audit purposes"""
    version = models.CharField(max_length=10, unique=True)  # e.g., "1.0", "1.1"
    content = models.TextField()
    effective_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Privacy Policy Version"
        verbose_name_plural = "Privacy Policy Versions"
    
    def __str__(self):
        return f"Privacy Policy v{self.version} ({self.effective_date})"

class PrivacyPolicyConsent(models.Model):
    """Records user consent to privacy policy"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='privacy_consents')
    policy_version = models.ForeignKey(PrivacyPolicyVersion, on_delete=models.PROTECT, null=True)  # Allow null temporarily
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Privacy Policy Consent"
        verbose_name_plural = "Privacy Policy Consents"
    
    def __str__(self):
        return f"{self.user.username} - v{self.policy_version.version} - {self.accepted_at}"
