import os
from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.static import static
from pinax.stripe.views import Webhook
import main_app.urls
import source.lib.lets_encrypt.urls


urlpatterns = [
    url(r"^payments/webhook/$", Webhook.as_view(), name="pinax_stripe_webhook"),
    url(r'login/', include('source.lib.shopify_auth.urls', namespace='shopify_auth')),
    url(r'API/', include('source.lib.shopify_webhook.urls', namespace='shopify_webhook')),
    url(r'^', include(main_app.urls, namespace='main_app')),
    url(r'^', include(source.lib.lets_encrypt.urls, namespace='lets_encrypt')),
]

# User-uploaded files like profile pics need to be served in development
# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if not 'ON_PRODUCTION' in os.environ:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
