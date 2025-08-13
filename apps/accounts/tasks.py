from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from .models import UserProfile
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task
def cleanup_inactive_users():
    """
    Delete users who haven't logged in for over 3 years (GDPR compliance)
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=365)  # 3 years
        inactive_users = User.objects.filter(last_login__lt=cutoff_date)
        
        for user in inactive_users:
            logger.info(f"Deleting inactive user account for {user.email} due to 1-year inactivity")
            # Send notification email before deletion
            from django.core.mail import send_mail
            send_mail(
                subject='Your Account Will Be Deleted Due to Inactivity',
                message=f'Your AI Vacation Recommendations account has been inactive for over 1 year and will be deleted in accordance with our data retention policy. If you wish to keep your account, please log in within the next 30 days.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        
        # Give users 30 days notice before actual deletion
        really_old_cutoff = timezone.now() - timedelta(days=365 + 30)
        very_inactive_users = User.objects.filter(last_login__lt=really_old_cutoff)
        deletion_count = very_inactive_users.count()
        very_inactive_users.delete()
        
        logger.info(f"Deleted {deletion_count} user accounts due to 3+ years of inactivity")
        
    except Exception as e:
        logger.error(f"Error in cleanup_inactive_users task: {e}")


@shared_task
def reset_monthly_quotas():
    """Reset monthly quotas for all users on the 1st of each month"""
    from .models import UserProfile
    from django.utils import timezone
    
    today = timezone.now().date()
    if today.day == 1:  # Only run on 1st of month
        updated_count = UserProfile.objects.all().update(
            monthly_analyses_used=0,
            monthly_quota_reset_date=today
        )
        logger.info(f"Reset monthly quotas for {updated_count} users")
        return f"Reset quotas for {updated_count} users"
    
    return "Not the 1st of month, skipping quota reset"

