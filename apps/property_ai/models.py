# apps/property_ai/models.py - Simple changes to existing model
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
import uuid
from django.utils import timezone

User = get_user_model()

class PropertyAnalysis(TimeStampedModel):
    """AI-powered property investment analysis for sale properties - NOW GLOBAL"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # CHANGED: Make user nullable and add scraped_by field
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_analyses', 
                           null=True, blank=True, help_text="User who requested this analysis")
    scraped_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='scraped_properties',
                                 help_text="User who initiated the scrape")
    
    # Core property identifiers - ADD UNIQUE CONSTRAINT
    property_url = models.URLField(unique=True)  # <-- CHANGED: Now unique globally
    property_id = models.CharField(max_length=50, blank=True)
    listing_code = models.CharField(max_length=50, blank=True)
    property_title = models.CharField(max_length=500)
    property_location = models.CharField(max_length=255)
    neighborhood = models.CharField(max_length=100, blank=True, null=True, help_text="Neighborhood/District")
    asking_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # KEEP ALL EXISTING FIELDS EXACTLY THE SAME...
    property_type = models.CharField(max_length=50, choices=[
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('commercial', 'Commercial'),
        ('office', 'Office'),
        ('studio', 'Studio'),
        ('land', 'Land'),
        ('business', 'Business'),
    ], blank=True)
    
    total_area = models.IntegerField(null=True, blank=True)
    internal_area = models.IntegerField(null=True, blank=True)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    floor_level = models.CharField(max_length=50, blank=True)
    ceiling_height = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    facade_length = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    property_condition = models.CharField(max_length=20, choices=[
        ('new', 'New'),
        ('used', 'Used'),
        ('renovation_needed', 'Needs Renovation'),
    ], blank=True)
    furnished = models.BooleanField(null=True, blank=True)
    has_elevator = models.BooleanField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    
    # Analysis results - ENHANCED
    analysis_result = models.JSONField(default=dict)
    ai_summary = models.TextField(blank=True)
    investment_score = models.IntegerField(
        null=True, blank=True, 
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    recommendation = models.CharField(max_length=20, choices=[
        ('strong_buy', 'Strong Buy'),
        ('buy', 'Buy'),
        ('hold', 'Hold'),
        ('avoid', 'Avoid')
    ], null=True, blank=True)
    
    # NEW: Enhanced analytics fields
    market_opportunity_score = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Market opportunity score (0-100)"
    )
    price_percentile = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Price percentile among comparable properties"
    )
    market_position_percentage = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Price position vs market average (%)"
    )
    negotiation_leverage = models.CharField(max_length=20, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], null=True, blank=True, help_text="Buyer's negotiation leverage")
    market_sentiment = models.CharField(max_length=20, choices=[
        ('bullish', 'Bullish'),
        ('neutral', 'Neutral'),
        ('bearish', 'Bearish')
    ], null=True, blank=True, help_text="Market sentiment at analysis time")
    
    STATUS_CHOICES = [
        ('analyzing', _('Analyzing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='analyzing')
    
    # KEEP ALL EXISTING FIELDS
    report_generated = models.BooleanField(default=False)
    report_file_path = models.CharField(max_length=500, blank=True)
    processing_stage = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="Property still available online")
    last_checked = models.DateTimeField(null=True, blank=True, help_text="Last time URL was verified")
    removed_date = models.DateTimeField(null=True, blank=True, help_text="When property was no longer accessible")
    
    agent_name = models.CharField(max_length=100, blank=True, null=True, 
                                help_text="Agent handling this property")
    agent_email = models.EmailField(blank=True, null=True, 
                                  help_text="Agent email contact")
    agent_phone = models.CharField(max_length=20, blank=True, null=True,
                                 help_text="Agent phone number")
    # ADD: Tier access control
    def is_available_to_user(self, user):
        """Global access control - all analyses are available based on tier"""
        if not user or not user.is_authenticated:
            return False
            
        user_profile = getattr(user, 'profile', None)
        if not user_profile:
            return False
            
        tier = user_profile.subscription_tier
        
        # All tiers can access their own analyses
        if self.user == user:
            return True
        
        # For global analyses (any analysis in the system)
        if tier == 'free':
            # Free: Can access any completed analysis
            return self.status == 'completed'
        elif tier == 'basic':  # This is your "Premium" tier
            # Basic: Can access any completed analysis
            return self.status == 'completed'
        elif tier == 'premium':  # This is your "Ultimate" tier
            # Premium: Can access any completed analysis
            return self.status == 'completed'
        else:
            return False
        
    # KEEP ALL EXISTING PROPERTIES AND METHODS
    @property
    def days_on_market(self):
        end_date = self.removed_date if self.removed_date else timezone.now()
        return (end_date - self.created_at).days
    
    @property
    def price_per_sqm(self):
        area = self.total_area
        if area and area > 0:
            return float(self.asking_price) / area
        return None
    
    @property
    def usable_area(self):
        return self.internal_area or self.total_area
    
    @property
    def is_commercial(self):
        return self.property_type in ['commercial', 'office', 'business']
    
    @property
    def location_tier(self):
        location_lower = self.property_location.lower()
        if any(area in location_lower for area in ['qendra', 'center', 'blloku', 'tirana', 'tiranë']):
            return 'prime'
        elif any(area in location_lower for area in ['durrës', 'durres', 'vlorë', 'vlore']):
            return 'good'
        else:
            return 'emerging'
    
    @property
    def investment_category(self):
        if self.investment_score and self.investment_score >= 80:
            return 'high_potential'
        elif self.investment_score and self.investment_score >= 60:
            return 'moderate_potential'
        else:
            return 'low_potential'
    
    @property
    def square_meters(self):
        return self.usable_area
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property_url']),  # Add URL index
            models.Index(fields=['property_location', 'property_type']),
            models.Index(fields=['asking_price']),
            models.Index(fields=['investment_score']),
            models.Index(fields=['status']),
            models.Index(fields=['scraped_by']),  # New index
            models.Index(fields=['agent_name']),
        ]
    
    def __str__(self):
        return f"Investment Analysis: {self.property_title}"
    
    

class ComingSoonSubscription(models.Model):
    """Simple email collection for coming soon page"""
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = "Coming Soon Subscription"
        verbose_name_plural = "Coming Soon Subscriptions"
    
    def __str__(self):
        return f"{self.email} ({self.subscribed_at.strftime('%Y-%m-%d')})"