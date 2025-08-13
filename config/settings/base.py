# config/settings/base.py
import os
from pathlib import Path
from dotenv import load_dotenv
from celery.schedules import crontab

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables
load_dotenv(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites', 
    'django.contrib.sitemaps',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'sorl.thumbnail',
    'anymail',
    'django.contrib.humanize',
    'social_django',
    'markdownify',
    'django_celery_beat',
    
    
]

LOCAL_APPS = [
    'apps.core.apps.CoreConfig',
    'apps.property_ai.apps.PropertyAiConfig', 
    'apps.accounts.apps.AccountsConfig',  # <-- add this line
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS + ['markdownx']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
     'apps.property_ai.middleware.MaintenanceModeMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'tourism'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Site framework
SITE_ID = 1

# API Keys for vacation AI system
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY')
IPN_SECRET = os.getenv('IPN_SECRET')

USE_GEMINI = True  # Set to True to use Gemini, False for Ollama
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Add to environment variables
GEMINI_MODEL = 'gemini-2.5-flash'  # or 'gemini-1.5-pro' for higher accuracy


# Encryption key for sensitive data
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'default-key-change-in-production')

EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'

ANYMAIL = {
    "MAILGUN_API_KEY": os.getenv("MAILGUN_ACCESS_KEY"),
    "MAILGUN_SENDER_DOMAIN": os.getenv("MAILGUN_DOMAIN"),
    "MAILGUN_API_URL": "https://api.eu.mailgun.net/v3",
}
DEFAULT_FROM_EMAIL = 'noreply@genvacation.com'



# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Add this line:
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'cleanup-inactive-users-daily': {
        'task': 'apps.accounts.tasks.cleanup_inactive_users',
        'schedule': crontab(hour=0, minute=0),  # every day at midnight
    },

    'daily-property-scrape': {
        'task': 'apps.property_ai.tasks.daily_property_scrape',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
        'options': {'queue': 'default'}
    },
    
    # Check property URLs every Sunday at 3 AM
    'check-property-urls': {
        'task': 'apps.property_ai.tasks.check_property_urls_task',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
    },

    # NEW: Bootstrap scraping
    'bootstrap-scraping': {
        'task': 'apps.property_ai.tasks.bootstrap_scrape_batch',
        'schedule': crontab(hour=1, minute=0),  # 1 AM daily
        'kwargs': {'pages_per_batch': 50}
    },
    
    
    # NEW: Maintenance scraping (runs after bootstrap complete)
    'nightly-maintenance': {
        'task': 'apps.property_ai.tasks.nightly_maintenance_scrape',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Social Auth Settings
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'apps.accounts.pipeline.record_privacy_policy_consent',  # <-- Add this line
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

SESSION_COOKIE_AGE = 86400  # 1 day
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Store in database

MAINTENANCE_MODE = True 