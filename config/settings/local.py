# config/settings/local.py
from .base import *

DEBUG = True

# Local-specific settings
CORS_ALLOW_ALL_ORIGINS = True

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'