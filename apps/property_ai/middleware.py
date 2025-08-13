from django.shortcuts import render
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip maintenance mode for admin and specific paths
        if getattr(settings, 'MAINTENANCE_MODE', False):
            allowed_paths = [
                '/admin/',
                '/static/',
                '/media/',
                '/favicon.ico',
            ]
            
            # Allow admin users to bypass maintenance mode
            if (request.user.is_authenticated and request.user.is_staff) or \
               any(request.path.startswith(path) for path in allowed_paths):
                return self.get_response(request)
            
            try:
                from .forms import ComingSoonForm
                from .models import ComingSoonSubscription
                
                # Handle subscription form POST
                if request.method == 'POST' and 'email' in request.POST:
                    form = ComingSoonForm(request.POST)
                    if form.is_valid():
                        form.save()
                        messages.success(request, 'Thanks! We\'ll notify you when we launch.')
                        return HttpResponseRedirect(request.path)
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{error}")
                        form = ComingSoonForm()
                else:
                    form = ComingSoonForm()
                
                # Get subscriber count for social proof
                subscriber_count = ComingSoonSubscription.objects.count()
                    
            except Exception:
                # Fallback form for when models aren't ready
                from django import forms
                
                class TempForm(forms.Form):
                    email = forms.EmailField(
                        widget=forms.EmailInput(attrs={
                            'class': 'form-control',
                            'placeholder': 'Enter your email',
                            'required': True
                        })
                    )
                
                form = TempForm()
                subscriber_count = 0
            
            # Show coming soon page
            return render(request, 'property_ai/coming_soon.html', {
                'form': form,
                'subscriber_count': subscriber_count
            }, status=503)
        
        return self.get_response(request)