from django.conf.urls import url

from source.lib.shopify_webhook.views import WebhookView


urlpatterns = [
    url(r'webhook/', WebhookView.as_view(), name = 'webhook'),        
]
