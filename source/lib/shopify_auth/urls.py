from django.conf.urls import url

from source.lib.shopify_auth import views

urlpatterns = [
  url(r'^finalize/$',     views.finalize, name='finalize'),
  url(r'^authenticate/$', views.authenticate, name='authenticate'),
  url(r'^$',              views.login, name='login'),
]