import os
import django
import sys

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

# Test the API key loading
from django.conf import settings
print(f"OPENAI_API_KEY defined in settings: {'OPENAI_API_KEY' in dir(settings)}")
print(f"OPENAI_API_KEY value: {getattr(settings, 'OPENAI_API_KEY', 'Not defined')}")

# Test the API directly
if getattr(settings, 'OPENAI_API_KEY', ''):
    import openai
    openai.api_key = settings.OPENAI_API_KEY
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "user", "content": "Hello world!"}
        ],
        max_tokens=50
    )
    print(f"API Test Result: {response.choices[0].message.content}")
else:
    print("Cannot test API - no key defined")