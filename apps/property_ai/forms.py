from django import forms
from .models import ComingSoonSubscription

class ComingSoonForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'required': True
        })
    )
    
    class Meta:
        model = ComingSoonSubscription
        fields = ['email']
    
    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if ComingSoonSubscription.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already subscribed!")
        return email