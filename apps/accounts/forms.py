from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="We'll never share your email with anyone else.",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    privacy_policy = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must accept the Privacy Policy to register.'},
        label="I agree to the Privacy Policy"
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "privacy_policy")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes and customize help text
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['username'].help_text = "150 characters or fewer. Letters, digits and @/./+/-/_ only."
        
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].help_text = "Must be 8+ characters and not too common."
        
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].help_text = None  # Remove help text for confirmation
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )