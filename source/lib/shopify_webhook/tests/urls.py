from django.conf.urls import patterns, url

from source.lib.shopify_webhook.views import WebhookView


urlpatterns = patterns('',
    url(r'webhook/', WebhookView.as_view(), name = 'webhook'),        
)
