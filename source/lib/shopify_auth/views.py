from base64 import b64encode
from os import urandom
from django.conf import settings
from django.contrib import auth
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, resolve_url, get_object_or_404, redirect
import source.lib.shopify as shopify
from .decorators import anonymous_required, login_required, url_kwargs_match_request_user, token_update_required
from django.core.cache import cache
import logging
from urlparse import urlparse, parse_qs
from source.lib.shopify_auth.helpers import add_query_parameters_to_url
from source.lib.shopify_auth.backends import ShopUserBackend


def get_return_address(request):
    shop_param = {}
    shop = getattr(request.user, "myshopify_domain", None)
    if shop:
        shop_param = {"shop" : shop}

    host = request.META.get("HTTP_HOST", None)
    referrer = request.META.get("HTTP_REFERER", None)

    if referrer:
        referrer = urlparse(referrer)

        if referrer.netloc.lower() == host.lower():
            query = parse_qs(referrer.query)
            redirect = query.get(auth.REDIRECT_FIELD_NAME, [""])[0]
            if redirect:
                return add_query_parameters_to_url(redirect, shop_param)

    return add_query_parameters_to_url(resolve_url(settings.LOGIN_REDIRECT_URL), shop_param)


def create_nonce(length=64):
    return filter(lambda s: s.isalpha(), b64encode(urandom(length * 2)))[:length]


@anonymous_required
def login(request, *args, **kwargs):

    # The `shop` parameter may be passed either directly in query parameters, or
    # as a result of submitting the login form.
    shop = request.POST.get('shop', request.GET.get('shop'))
    # If the shop parameter has already been provided, attempt to authenticate immediately.
    if shop:
        return authenticate(request, *args, **kwargs)

    # Get the current Shopify App Store URL
    SHOPIFY_APP_STORE_URL = settings.SHOPIFY_APP_STORE_URL
    APP_MARKETING_URL = settings.APP_MARKETING_URL

    return render(request, "shopify_auth/login.html", {
        'SHOPIFY_APP_NAME': settings.SHOPIFY_APP_NAME,
        'SHOPIFY_APP_STORE_URL': SHOPIFY_APP_STORE_URL,
        'APP_MARKETING_URL': APP_MARKETING_URL
    })


@anonymous_required
def authenticate(request, *args, **kwargs):

    shop = request.POST.get('shop', request.GET.get('shop'))

    if shop:
        redirect_uri = request.build_absolute_uri(reverse('shopify_auth:finalize'))

        scope = settings.SHOPIFY_APP_API_SCOPE

        # Create a state nonce
        temp_nonce = create_nonce()

        # Store the nonce in memcache to check later (for this user/shop)
        if 'https://' in shop.lower():
            shop = shop[8:]
        elif 'http://' in shop.lower():
            shop = shop[7:]
        elif '.myshopify.com' not in shop.lower():
            return HttpResponseRedirect(reverse('shopify_auth:login'))

        # Store the nonce in memcache to check later (for this user/shop)
        key_name = str(shop) + "_nonce"
        cache.set(key=key_name, value=temp_nonce, timeout=600)

        permission_url = shopify.Session(shop.strip()).create_permission_url(scope, redirect_uri, state=temp_nonce)

        if settings.SHOPIFY_APP_IS_EMBEDDED:
            # Embedded Apps should use a Javascript redirect.
            return render(request, "shopify_auth/iframe_redirect.html", {
                'shop': shop,
                'redirect_uri': permission_url
            })
        else:
            # Non-Embedded Apps should use a standard redirect.
            return HttpResponseRedirect(permission_url)
    else:
        shop = request.GET.get('shop')
        if shop:
            return finalize(request, *args, **kwargs)

    return_address = get_return_address(request)
    return HttpResponseRedirect(return_address)


@anonymous_required
def finalize(request, *args, **kwargs):
    shop = request.POST.get('shop', request.GET.get('shop'))

    state = request.GET.get('state', None)
    key_name = str(shop) + "_nonce"
    original_nonce = cache.get(key_name)

    if not state or not original_nonce or state != original_nonce:
        logging.error('OAUTH-FINALIZE-FOR-{0}: There was an issue with the state of this request.'.format(shop))
        login_url = reverse('shopify_auth:login')
        return HttpResponseRedirect(login_url)

    try:
        shopify_session = shopify.Session(shop, token=kwargs.get('token'))
        shopify_session.request_token(request.GET)
    except Exception as e:
        login_url = reverse('shopify_auth:login')
        return HttpResponseRedirect(login_url)

    # Attempt to authenticate the user and log them in.
    user = auth.authenticate(myshopify_domain=shopify_session.url, token=shopify_session.token)

    if user:

        auth.login(request, user)
        return redirect(reverse("main_app:home_page", kwargs={'store_url': user.store_url_str()}) )

    login_url = reverse('shopify_auth:login')
    return HttpResponseRedirect(login_url)