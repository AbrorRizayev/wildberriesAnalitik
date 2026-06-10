"""
Django settings for AIRA (Wildberries Analytics).
"""

from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ('1', 'true', 'yes', 'on')


# ============ Security ============
SECRET_KEY = env('SECRET_KEY', 'django-insecure-dev-only-change-me')
DEBUG = env_bool('DEBUG', True)
ALLOWED_HOSTS = [h.strip() for h in env('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# Origins trusted for unsafe (POST) requests — needed when the site is reached
# over HTTPS through a tunnel/proxy whose host differs from the bound address.
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]


# ============ Apps ============
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'apps.accounts',
    'apps.reports',
    'apps.analytics',
    'apps.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ============ Templates (Django Template Language) ============
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'apps.accounts.context_processors.profile',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ============ Database (PostgreSQL) ============
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', 'aira'),
        'USER': env('DB_USER', 'aira'),
        'PASSWORD': env('DB_PASSWORD', 'aira'),
        'HOST': env('DB_HOST', '127.0.0.1'),
        'PORT': env('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}


# ============ Auth ============
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'analytics:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ============ i18n ============
LANGUAGE_CODE = 'ru'
TIME_ZONE = env('TIME_ZONE', 'Asia/Tashkent')
USE_I18N = True
USE_TZ = True

# Supported UI languages (Russian / Uzbek). The chosen language is stored by
# the set_language view (session + cookie) and applied by LocaleMiddleware.
from django.utils.translation import gettext_lazy as _  # noqa: E402

LANGUAGES = [
    ('ru', _('Русский')),
    ('uz', _("O'zbekcha")),
]
LOCALE_PATHS = [BASE_DIR / 'locale']


# ============ Static ============
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============ Uploads (temporary — files are NEVER stored permanently) ============
# Excel max 30 MB. Parsed in-request for MVP, temp file deleted after.
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # >5MB streams to a temp file on disk

# ============ Production security (active when DEBUG=False) ============
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    X_FRAME_OPTIONS = 'DENY'