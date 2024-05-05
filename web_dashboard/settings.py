"""
Django settings for web project.

Generated by 'django-admin startproject' using Django 5.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
import dj_database_url

from pathlib import Path
from setuptools._distutils.util import strtobool

from dotenv import load_dotenv

# Load local enviroment .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(strtobool(os.getenv('DEBUG', 'False')))

LOCAL_HOST = os.getenv('HOST')

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'webserver',
    LOCAL_HOST,
]

# EXTERNAL_HOSTNAME is used on external deploy services like render.com
EXTERNAL_HOSTNAME = os.getenv('EXTERNAL_HOSTNAME')
if EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(EXTERNAL_HOSTNAME)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    "whitenoise.runserver_nostatic",
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django_extensions',
    'django_bootstrap5',
    'phonenumber_field',
    'location_field.apps.DefaultConfig',
    'axes',
    'web_dashboard',
    'web_dashboard.custom_auth',
    'web_dashboard.users',
    'web_dashboard.search_requests',
    "web_dashboard.logistics",
    "web_dashboard.bot_api",
    "crispy_forms",
    "crispy_bootstrap5",
    ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

# Rollbar errors notifier
# At the moment it is not set up
# if not DEBUG:
#     MIDDLEWARE.append(
#         'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
#     )

# ROLLBAR = {
#     'access_token': os.getenv('ROLLBAR_TOKEN', False),
#     'environment': 'development' if DEBUG else 'production',
#     'code_version': '1.0',
#     'root': BASE_DIR,
# }

ROOT_URLCONF = 'web_dashboard.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'web_dashboard.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv(
            'DATABASE_URL',
            'postgis://postgres:postgres@localhost:5432/postgres'
        ),
        conn_max_age=600
    )
}

SQLITE_SETTINGS = {
    # 'ENGINE': 'django.db.backends.sqlite3',
    'ENGINE': 'django.contrib.gis.db.backends.spatialite',
    'NAME': BASE_DIR / 'db.sqlite3',
}

if os.getenv('DB_ENGINE', 'SQLite') == 'SQLite':
    DATABASES['default'] = SQLITE_SETTINGS


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',  # noqa: E501
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',  # noqa: E501
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',  # noqa: E501
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',  # noqa: E501
    },
]

# Authentification settings
# https://docs.djangoproject.com/en/5.0/ref/settings/#sessions

AUTH_USER_MODEL = 'users.CustomUser'
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

SESSION_COOKIE_AGE = 60 * 60 * 24  # 24 hours in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# AXES settings
# https://django-axes.readthedocs.io/en/latest/index.html
AXES_FAILURE_LIMIT = int(os.getenv("LOGIN_FAILURE_LIMIT", 5))
AXES_COOLOFF_TIME = int(os.getenv('COOLDOWN_TIME', 2))  # Hours

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'ru-RU'

LANGUAGES = [
    ('en', 'English'),
    ('ru', 'Russian'),
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Map and location
# https://github.com/caioariede/django-location-field
# https://django-leaflet.readthedocs.io/en/latest/
LOCATION_FIELD = {
    'search.provider': 'yandex',
    'search.suffix': '',

    # Yandex (Only Search Provider is available)
    # https://yandex.com/dev/maps/jsapi/doc/2.1/quick-start/index.html#get-api-key
    'provider.yandex.api_key': os.getenv('YMAP_TOKEN')
}


# Media
# https://docs.djangoproject.com/en/5.0/ref/settings/#media-root
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Crispy forms
# https://django-crispy-forms.readthedocs.io
# https://github.com/django-crispy-forms/crispy-bootstrap5
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Django - Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DJANGO_TG_TOKEN = os.getenv("DJANGO_TG_TOKEN")
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
