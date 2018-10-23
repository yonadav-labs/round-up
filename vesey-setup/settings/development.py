# Development file
import raven
from .base import *             # NOQA
import os
import dj_database_url
import json
from django.core.exceptions import ImproperlyConfigured

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
    ENV_JSON = json.loads(os.environ.get('DEVELOPMENT_ENV', None))
else:
    LOCAL_ENV_LOCATION = dirname(dirname(dirname(dirname(__file__))))
    env_file = join(LOCAL_ENV_LOCATION, 'veseyenvironment.json')
    if not exists(env_file):
        raise ImproperlyConfigured("No local environment file was found in directory: {0}".format(LOCAL_ENV_LOCATION))

    with open(env_file) as data_file:
        ENV_JSON = json.load(data_file)

if not ENV_JSON:
    raise ImproperlyConfigured("No environment variables were found")


##############################
# Django Debug Settings
##############################

# For security and performance reasons, DEBUG is turned off
if on_heroku:
    DEBUG = False
    TEMPLATES[0]['OPTIONS'].update({'debug': False})
else:
    DEBUG = True
    TEMPLATES[0]['OPTIONS'].update({'debug': True})

# Define STATIC_ROOT for the collectstatic command
STATIC_ROOT = join(BASE_DIR, '..', 'site', 'static')

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
            'NAME': 'd4p8mgk2jr73vg',
            'USER': 'ue5r9kocrf15s',
            'PASSWORD': ENV_JSON.get('DATABASE_PW', None),
            'HOST': 'ec2-35-172-93-161.compute-1.amazonaws.com',
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
    SHOPIFY_APP_API_KEY = "89ffc21853e35ef52903ba5303116056"

if on_heroku:
    SHOPIFY_APP_API_SECRET = ENV_JSON.get('SHOPIFY_APP_SECRET_KEY', None)
else:
    SHOPIFY_APP_API_SECRET = "9435e97c2766d3f84a6b37d20cb72084"

APP_BASE_URL = ['2ec50f46.ngrok.io', 'vesey.herokuapp.com', 'roundup.vesey.org']

if on_heroku:
    PINAX_STRIPE_PUBLIC_KEY =  ENV_JSON.get('PINAX_STRIPE_PUBLIC_KEY', None)
    PINAX_STRIPE_SECRET_KEY = ENV_JSON.get('PINAX_STRIPE_SECRET_KEY', None)
else:
    PINAX_STRIPE_PUBLIC_KEY =  "pk_test_MdT8kDDvz9IYFREkTU5LKMao"
    PINAX_STRIPE_SECRET_KEY = "sk_test_ZNtufU4ueQViSlwh0kx71yXG"

AWS_ACCESS_KEY_ID = ENV_JSON.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = ENV_JSON.get('AWS_SECRET_ACCESS_KEY', None)

OPEN_EXCHANGE_APP_ID = ENV_JSON.get('OPEN_EXCHANGE_APP_ID', None)

RAVEN_CONFIG = {
    'dsn': 'https://300e85eb6cfa48ac8ea206b6a5bbcf61:ec03c8d4c8274cb59d1234cf5e9d2d36@sentry.io/282002',
}

if on_heroku:
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', None)
else:
    CELERY_BROKER_URL = ENV_JSON.get('CELERY_BROKER', None)