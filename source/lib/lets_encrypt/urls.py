from django.conf.urls import url

from source.lib.lets_encrypt import views


urlpatterns = [
    url(r'^\.well-known/acme-challenge/(?P<url_slug>[a-zA-z0-9_-]+)$', views.secret, name='secret'),
    ]