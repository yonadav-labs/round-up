# In production set the environment variable like this:
#    DJANGO_SETTINGS_MODULE=my_proj.settings.production
import json
import os
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from .base import *             # NOQA

##############################
# Environment File source and server settings
##############################

on_heroku = False
if 'ON_HEROKU_SERVER' in os.environ:
  on_heroku = True

ON_PRODUCTION = False
if 'ON_PRODUCTION' in os.environ:
  ON_PRODUCTION = True

if on_heroku:
    ENV_JSON = json.loads(os.environ.get('PRODUCTION_ENV', None))
else:
    LOCAL_ENV_LOCATION = dirname(dirname(dirname(dirname(__file__))))
    env_file = join(LOCAL_ENV_LOCATION, 'veseyenvironment.json')
    if not exists(env_file):
        raise ImproperlyConfigured("No local environment file was found in directory: {0}".format(LOCAL_ENV_LOCATION))

    with open(env_file) as data_file:
        ENV_JSON = json.load(data_file)

if not ENV_JSON:
    raise ImproperlyConfigured("No environment variables were found")

# For security and performance reasons, DEBUG is turned off
DEBUG = False
TEMPLATES[0]['OPTIONS'].update({'debug': False})

# Cache the templates in memory for speed-up
loaders = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

TEMPLATES[0]['OPTIONS'].update({"loaders": loaders})
TEMPLATES[0].update({"APP_DIRS": False})

# Define STATIC_ROOT for the collectstatic command
STATIC_ROOT = 'static'

if on_heroku:
    from memcacheify import memcacheify

    # memcache for heroku
    CACHES = memcacheify()

else:
    # Memcache local
    CACHES = {
        'default': {
            'BACKEND': 'django_bmemcached.memcached.BMemcached',
            'LOCATION': 'mc2.dev.ec2.memcachier.com:11211',
            'OPTIONS': {
                'username': '0E4A69',
                'password': ENV_JSON.get('MEMCACHE_PW', None),
            }
        }
    }


if on_heroku:
    # Running on production Heroku, so use a PostGres Server
    # Update database configuration with $DATABASE_URL.
    DATABASES = {}
    DATABASES['default'] = dj_database_url.config(conn_max_age=500)
else:
    # To Run Locally (Password needs to move to .env)
     DATABASES = {
         'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'dflnj78idmeik9',
            'USER': 'hlcfsbcakzcnxq',
            'PASSWORD': ENV_JSON.get('DATABASE_PW', None),
            'HOST': 'ec2-54-235-148-19.compute-1.amazonaws.com',
            'PORT': '5432',
         }
     }
# END DATABASE ##

SECRET_KEY = ENV_JSON.get('DJANGO_SECRET_KEY', None)

# Must mention ALLOWED_HOSTS in production!
# SECURITY WARNING: App Engine's security features ensure that it is safe to
# have ALLOWED_HOSTS = ['*'] when the app is deployed. If you deploy a Django
# app not on App Engine, make sure to set an appropriate host here.
# See https://docs.djangoproject.com/en/1.10/ref/settings/
ALLOWED_HOSTS = ["*"]

if on_heroku:
    SHOPIFY_APP_API_KEY = ENV_JSON.get('SHOPIFY_APP_PUBLIC_KEY', None)
else:
    SHOPIFY_APP_API_KEY = ENV_JSON.get('SHOPIFY_APP_PUBLIC_KEY', None)

if on_heroku:
    SHOPIFY_APP_API_SECRET = ENV_JSON.get('SHOPIFY_APP_SECRET_KEY', None)
else:
    SHOPIFY_APP_API_SECRET = ENV_JSON.get('SHOPIFY_APP_SECRET_KEY', None)

APP_BASE_URL = ['vesey.herokuapp.com', 'roundup.vesey.org']

PINAX_STRIPE_PUBLIC_KEY =  ENV_JSON.get('PINAX_STRIPE_PUBLIC_KEY', None)
PINAX_STRIPE_SECRET_KEY = ENV_JSON.get('PINAX_STRIPE_SECRET_KEY', None)

AWS_ACCESS_KEY_ID = ENV_JSON.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = ENV_JSON.get('AWS_SECRET_ACCESS_KEY', None)

OPEN_EXCHANGE_APP_ID = ENV_JSON.get('OPEN_EXCHANGE_APP_ID', None)

RAVEN_CONFIG = {
    'dsn': 'https://300e85eb6cfa48ac8ea206b6a5bbcf61:ec03c8d4c8274cb59d1234cf5e9d2d36@sentry.io/282002',
}

CELERY_BROKER_URL = ENV_JSON.get('CELERY_BROKER', None)