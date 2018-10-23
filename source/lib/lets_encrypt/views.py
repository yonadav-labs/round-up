# THIRD PARTY
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from source.lib.shopify_auth.decorators import anonymous_required
from source.lib.lets_encrypt.models import Secret


@anonymous_required
def secret(request, url_slug):
    """ Serves the secret that Let's Encrypt requires us to serve in order to validate that we own
        the domain.

        #example url:
            https://[app-url].com/ENCRYPT/.well-known/acme-challenge/test-slug
    """
    secret = get_object_or_404(Secret, url_slug=url_slug)
    return HttpResponse(secret.secret)

