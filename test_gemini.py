import os
import django
import sys

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

# Test the API key loading
from django.conf import settings
print(f"GEMINI_API_KEY defined in settings: {'GEMINI_API_KEY' in dir(settings)}")
print(f"GEMINI_API_KEY value: {getattr(settings, 'GEMINI_API_KEY', 'Not defined')}")

# Test the API directly
if getattr(settings, 'GEMINI_API_KEY', ''):
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("Hello world!")
    print(f"API Test Result: {response.text}")
else:
    print("Cannot test API - no key defined")