"""
Django settings for my_proj project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""
from django.core.urlresolvers import reverse_lazy
from os.path import dirname, join, exists

# Build paths inside the project like this: join(BASE_DIR, "directory")
BASE_DIR = dirname(dirname(dirname(__file__)))
MEDIA_ROOT = join(BASE_DIR, 'media')
MEDIA_URL = "/media/"

# Use this to disable goolge modules to make migration on local possible (True to disable)

# Use Django templates using the new Django 1.8 TEMPLATES settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'source.lib.shopify_auth.context_processors.shopify_auth',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    # Disable Django's own staticfiles handling in favour of WhiteNoise, for
    # greater consistency between gunicorn and `./manage.py runserver`. See:
    # http://whitenoise.evans.io/en/stable/django.html#using-whitenoise-in-development
    # 'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'pinax.stripe',
    'crispy_forms',
    'source.lib.shopify_auth',
    'source.lib.bootstrap3_datetime',
    'djmoney',
    'django_countries',
    'main_app',
    'source.lib.lets_encrypt',
    'django_tables2',
    'django_filters',
    'django_bootstrap_breadcrumbs',
    'django_extensions',
    'storages',
    'easy_thumbnails',
    'corsheaders',
    'raven.contrib.django.raven_compat',
    'celery')

MIDDLEWARE_CLASSES = (
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'main_app.middleware.multi_session_middleware.MultiShopSessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'main_app.middleware.get_user_timezone.get_user_timezone',
)

ROOT_URLCONF = 'vesey-setup.urls'

WSGI_APPLICATION = 'vesey-setup.wsgi.application'
     
# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = 'static'
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'

# Crispy Form Theme - shopify polaris (based on bootstrap 3)
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# For Bootstrap 3, change error alert to 'danger'
from django.contrib import messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Use the Shopify Auth authentication backend.
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'source.lib.shopify_auth.backends.ShopUserBackend',
)

# Authentication Settings
AUTH_USER_MODEL = 'main_app.AuthAppShopUser'
# Set a default login redirect location.
LOGIN_REDIRECT_URL = reverse_lazy('main_app:login_redirect')

# Add Shopify Auth configuration.
#
# Note that sensitive credentials SHOPIFY_APP_API_KEY and SHOPIFY_APP_API_SECRET are read from environment variables,
# as is best practice. These environment variables are in turn read from a .env file in the project directory.
# See https://github.com/theskumar/python-dotenv for more
SHOPIFY_APP_NAME = 'Round Up - Support Local Non-Profits'
SHOPIFY_APP_STORE_URL = 'https://apps.shopify.com/round-up-seamlessly-support-local-non-profits'
SHOPIFY_APP_API_SCOPE = ['read_products', 'write_products', 'read_orders', 'read_themes', 'write_themes',
                         'read_script_tags', 'write_script_tags']
SHOPIFY_APP_IS_EMBEDDED = True
SHOPIFY_APP_DEV_MODE = False
SHOPIFY_MAX_RETRIES = 3
SHOPIFY_RETRY_WAIT = 0.5
SHOPIFY_MIN_TOKENS = 5
APP_MARKETING_URL = 'https://www.vesey.org/'

# Set secure proxy header to allow proper detection of secure URLs behind a proxy.
# See https://docs.djangoproject.com/en/1.7/ref/settings/#secure-proxy-ssl-header
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

DEFAULT_SUBSCRIPTION_PK = 1
CHARGE_ACTIVE = 'active'
CHARGE_ACCEPTED = 'accepted'
CHARGE_PENDING = 'pending'
CHARGE_CANCELLED = 'cancelled'
CHARGE_FROZEN = 'frozen'

DEFAULT_FIELD_PK = 16

# settings.py
SITE_ID = 1

##################################
# File storage settings
##################################

DEFAULT_FILE_STORAGE = THUMBNAIL_DEFAULT_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'vesey-app-storage'
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_FILE_OVERWRITE = False

##################################
# Thumbnail settings
##################################

THUMBNAIL_ALIASES = {
    '': {
        'charity_logo': {'size': (100, 50), 'background': 'white'},
    },
}

DEFAULT_IMAGE_LOCATION = "https://roundup.vesey.org/static/site/images/RoundUpIcon.png"

CORS_ORIGIN_ALLOW_ALL = True

ROUND_UP_DEFAULT_PRICE = 0.01
PINAX_STRIPE_DEFAULT_PLAN = 'low-volume-round-up-plan'
PINAX_STRIPE_HIGH_VOLUME_PLAN = 'high-volume-round-up-plan'
DEFAULT_CURRENCY = 'USD'
PINAX_STRIPE_HOOKSET = "main_app.hooks_stripe.HookSet"

EMAIL_BACKEND = 'django_amazon_ses.EmailBackend'
DEFAULT_FROM_EMAIL = PINAX_STRIPE_INVOICE_FROM_EMAIL = 'Round Up <shopifyroundup@gmail.com>'
HELP_TO_MAILBOX_EMAIL = 'shopifyroundup@gmail.com'

# TODO If Memory leak keeps occuring on task check out this thread: https://github.com/celery/celery/issues/3339
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_CONCURRENCY=1
CELERYD_MAX_TASKS_PER_CHILD = 10

SHOPIFY_PARTNER_ID = "655115"