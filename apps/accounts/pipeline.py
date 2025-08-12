from .models import PrivacyPolicyVersion, PrivacyPolicyConsent, UserProfile
import secrets
from django.utils import timezone

def record_privacy_policy_consent(strategy, details, user=None, *args, **kwargs):
    if user:
        # 1. Create UserProfile if it doesn't exist (for social auth users)
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'email_verification_token': secrets.token_urlsafe(32),
                'email_verification_sent_at': timezone.now(),
                'is_email_verified': True  # Auto-verify for Google users
            }
        )
        
        # 2. Create privacy policy consent if it doesn't exist
        if not PrivacyPolicyConsent.objects.filter(user=user).exists():
            current_policy = PrivacyPolicyVersion.objects.filter(is_active=True).first()
            if not current_policy:
                current_policy = PrivacyPolicyVersion.objects.order_by('-effective_date').first()
            
            PrivacyPolicyConsent.objects.create(
                user=user,
                policy_version=current_policy,
                ip_address=strategy.request.META.get('REMOTE_ADDR', ''),
                user_agent=strategy.request.META.get('HTTP_USER_AGENT', '')
            )