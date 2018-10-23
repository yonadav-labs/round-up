from functools import wraps
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.encoding import force_str
from django.shortcuts import resolve_url
from django.contrib.auth.decorators import login_required as django_login_required
from django.http.response import HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from main_app.helpers.external_helpers.shopify_webhook_controller import create_or_update_webhooks
from main_app.helpers.helpers import create_or_assert_round_up_product, create_or_assert_round_up_asset
from source.lib.pyactiveresource.connection import UnauthorizedAccess
import source.lib.shopify as shopify
from source.lib.shopify.resources.shop import Shop
from source.lib.shopify_auth.helpers import add_query_parameters_to_url, build_url


def anonymous_required(function=None, redirect_url=None):
    """
    Decorator requiring the current user to be anonymous (not logged in).
    """
    if not redirect_url:
        redirect_url = settings.LOGIN_REDIRECT_URL

    actual_decorator = user_passes_test(
        lambda u: u.is_anonymous(),
        login_url=redirect_url,
        redirect_field_name=None
    )

    if function:
        return actual_decorator(function)
    return actual_decorator


def login_required(f, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Decorator that wraps django.contrib.auth.decorators.login_required, but supports extracting Shopify's authentication
    query parameters (`shop`, `timestamp`, `signature` and `hmac`) and passing them on to the login URL (instead of just
    wrapping them up and encoding them in to the `next` parameter).

    This is useful for ensuring that users are automatically logged on when they first access a page through the Shopify
    Admin, which passes these parameters with every page request to an embedded app.
    """

    @wraps(f)
    def wrapper(request, *args, **kwargs):

        if request.user.is_authenticated():
            return f(request, *args, **kwargs)

        # Extract the Shopify-specific authentication parameters from the current request.
        shopify_params = {
            k: request.GET[k]
            for k in ['shop', 'timestamp', 'signature', 'hmac']
            if k in request.GET
        }

        # Get the login URL.
        resolved_login_url = force_str(resolve_url(login_url or settings.LOGIN_URL))

        # Add the Shopify authentication parameters to the login URL.
        updated_login_url = add_query_parameters_to_url(resolved_login_url, shopify_params)

        django_login_required_decorator = django_login_required(redirect_field_name=redirect_field_name,
                                                                login_url=updated_login_url)
        return django_login_required_decorator(f)(request, *args, **kwargs)

    return wrapper


def url_kwargs_match_request_user(f, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Decorator that ensures that a user has an active app subscription, if not, redirects user to the confirm screen \
    (and if the user isn't logged in, redirects them to the login process).

    This is useful for ensuring that users are active.
    """

    @wraps(f)
    def wrapper(request, *args, **kwargs):

        if request.user.store_url_str() == kwargs.get("store_url", None):
            return f(request, *args, **kwargs)

        raise PermissionDenied

    return wrapper


def token_update_required(f, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    A Decorator that ensures that a users shopify token has not been invalidated due to a delayed uninstall webhook or some
    malicious action.
    This is useful for ensuring that users are STILL active.
    """
    @wraps(f)
    def wrapper(request, *args, **kwargs):

        try:
            if request.user.adminprofile.is_admin:
                return f(request, *args, **kwargs)
        except ObjectDoesNotExist:
            pass

        with request.user.session:
            try:
                shop = Shop.current()

                # Create and manage the uninstall/update webhooks.
                create_or_update_webhooks(request.user, request.build_absolute_uri(reverse('shopify_webhook:webhook')))

                # Create a round up product for the app to handle round ups.
                create_or_assert_round_up_product(request.user)
                create_or_assert_round_up_asset(request.user)

                return f(request, *args, **kwargs)
            except UnauthorizedAccess:

                request.user.token = '00000000000000000000000000000000'
                request.user.save()

                # Invalidate any existing user sessions.
                request.user.clear_user_sessions()

                try:
                    shop = kwargs.get('store_url', request.user)
                except:
                    shop = None

                redirect_url = build_url('shopify_auth:login', get={'shop': shop})

                return HttpResponseRedirect(redirect_url)

    return wrapper


def setup_required(f, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Decorator that ensures that a user has an active app subscription, if not, redirects user to the confirm screen \
    (and if the user isn't logged in, redirects them to the login process).

    This is useful for ensuring that users are active.
    """

    @wraps(f)
    def wrapper(request, *args, **kwargs):
        try:
            if not request.user.userprofile.setup_required:
                return f(request, *args, **kwargs)
        except ObjectDoesNotExist:
            pass

        redirect_url = reverse("main_app:onboarding_wizard", kwargs={'store_url': request.user.store_url_str()})
        return HttpResponseRedirect(redirect_url)

    return wrapper