from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm
import secrets
from django.utils import timezone
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib import messages
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from .models import UserProfile, PrivacyPolicyConsent, PrivacyPolicyVersion
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.core.mail import send_mail
import logging
from .utils import record_page_view

# Set up logger
logger = logging.getLogger(__name__)

def register(request):
    if request.method == "GET":
        record_page_view(request, 'registration')

    if request.method == "POST":

        record_page_view(request, 'registration_attempt')
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            record_page_view(request, 'registration_success')
            
            # Create profile and token
            token = secrets.token_urlsafe(32)
            profile = UserProfile.objects.create(
                user=user,
                email_verification_token=token,
                email_verification_sent_at=timezone.now()
            )
            
            # Send verification email
            current_site = get_current_site(request)
            verification_url = request.build_absolute_uri(
                reverse('accounts:verify_email', args=[token])
            )
            subject = 'Verify your email'
            html_message = render_to_string('accounts/emails/email_verification.html', {
                'verification_url': verification_url,
                'user': user,
                'domain': current_site.domain,
                'privacy_policy_url': request.build_absolute_uri(reverse('accounts:privacy_policy')),
            })
            email = EmailMultiAlternatives(
                subject=subject,
                body=f"Click this link to verify your email: {verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            # Log the registration for GDPR compliance
            logger.info(f"New user registration: {user.username} (ID: {user.id}) with email {user.email}")
            
            messages.success(request, 'Account created. Check your email for verification.')
            
            # Redirect to a registration success page instead of login
            return render(request, 'accounts/register_success.html', {'email': user.email})
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})

@login_required
def user_profile(request):
    
    from apps.property_ai.models import PropertyAnalysis
    
    # Get user's analyses
    analyses = PropertyAnalysis.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, "accounts/profile.html", {
        "user": request.user,
        "analyses": analyses,
    })

def verify_email(request, token):
    try:
        profile = UserProfile.objects.get(email_verification_token=token)
        if not profile.is_email_verified:
            profile.is_email_verified = True
            profile.save()
            messages.success(request, 'Email verified! You can now log in.')
        else:
            messages.info(request, 'Email was already verified.')
        return redirect('accounts:login')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('accounts:login')

def login_view(request):
    if request.method == "POST":
        form = LoginForm(data=request.POST)  # Changed to use data parameter
        if form.is_valid():
            user = form.get_user()  # Use get_user() method from AuthenticationForm
            # Check if email is verified
            profile = UserProfile.objects.get(user=user)
            if not profile.is_email_verified:
                messages.error(request, 'Please verify your email before logging in.')
                return redirect('accounts:login')
            
            login(request, user)
            return redirect('accounts:user_profile')
        else:
            # Form validation errors will be displayed in the template
            pass
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})

@login_required
def delete_profile_confirm(request):
    """Show delete profile confirmation page"""
    return render(request, 'accounts/delete_profile_confirm.html', {
        'user': request.user,
    })

@login_required
@require_POST
def delete_profile_execute(request):
    """Actually delete the user profile and all data"""
    user = request.user
    user_email = user.email
    try:
        logger.info(f"User {user_email} requested profile deletion")
        
        # Log the privacy consents being deleted for audit purposes
        privacy_consents = user.privacy_consents.all()
        if privacy_consents.exists():
            logger.info(f"Deleting {privacy_consents.count()} privacy consent records for user {user_email}")
        
        send_mail(
            subject='Profile Deletion Confirmed',
            message=f'Your profile and all associated data have been permanently deleted from our service. Thank you for using our service.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=True
        )
        
        # The user.delete() call will cascade to delete related objects including privacy consents
        logout(request)
        user.delete()
        
        messages.success(request, 'Your profile has been successfully deleted. Thank you for using our service.')
        return redirect('property_ai:home')
    except Exception as e:
        logger.error(f"Profile deletion failed for {user_email}: {e}")
        messages.error(request, 'An error occurred while deleting your profile. Please try again.')
        return redirect('accounts:user_profile')


def privacy_policy(request):
    """Display the current privacy policy"""
    policy = PrivacyPolicyVersion.objects.filter(is_active=True).first()
    if not policy:
        policy = PrivacyPolicyVersion.objects.order_by('-effective_date').first()
    
    return render(request, 'accounts/privacy_policy.html', {
        'policy': policy
    })

@login_required
def view_accepted_policy(request):
    """Show the user the version of the privacy policy they accepted"""
    try:
        # Get the most recent consent record for this user
        consent = request.user.privacy_consents.select_related('policy_version').latest('accepted_at')
        return render(request, 'accounts/accepted_policy.html', {
            'consent': consent,
            'policy': consent.policy_version
        })
    except PrivacyPolicyConsent.DoesNotExist:
        messages.warning(request, "No record of privacy policy acceptance found.")
        return redirect('accounts:privacy_policy')

