"""
WSGI config for my_proj project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/
"""
import os
from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

if 'ON_PRODUCTION' in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vesey-setup.settings.production')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vesey-setup.settings.development')

application = get_wsgi_application()
application = DjangoWhiteNoise(application)

from django.core.cache.backends.memcached import BaseMemcachedCache
BaseMemcachedCache.close = lambda self, **kwargs: None

# Wrap werkzeug debugger if DEBUG is on
from django.conf import settings
if settings.DEBUG:
    try:
        import django.views.debug
        import six
        from werkzeug.debug import DebuggedApplication

        def null_technical_500_response(request, exc_type, exc_value, tb):
            six.reraise(exc_type, exc_value, tb)

        django.views.debug.technical_500_response = null_technical_500_response
        application = DebuggedApplication(application, evalex=True)
    except ImportError:
        pass
