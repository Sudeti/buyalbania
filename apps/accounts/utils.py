# apps/accounts/utils.py
from django.utils import timezone
from .models import PageView

def record_page_view(request, page_name):
    """Record a page view with analytics data"""
    try:
        # Ensure session exists for anonymous users
        if not request.session.session_key:
            request.session.save()
        
        PageView.objects.create(
            page_name=page_name,
            url_path=request.get_full_path(),
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referrer=request.META.get('HTTP_REFERER'),
            session_key=request.session.session_key
        )
    except Exception as e:
        # Log error but don't break the page
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to record page view for {page_name}: {e}")

def get_client_ip(request):
    """Get the real IP address of the client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip