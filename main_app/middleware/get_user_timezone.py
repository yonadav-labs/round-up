import pytz
from django.utils import timezone
from django.core.urlresolvers import resolve

class get_user_timezone(object):
    def process_request(self, request):

        admin_request = False
        current_url_name = resolve(request.path_info).url_name
        if current_url_name and 'admin' in current_url_name:
            admin_request = True

        if request.user.is_authenticated() and not admin_request:
            shopify_user_timezone = pytz.timezone(request.user.userprofile.iana_timezone)

            if shopify_user_timezone:
                 timezone.activate(shopify_user_timezone)
            else:
                 timezone.deactivate()
        elif admin_request:
            timezone.activate('America/New_York')