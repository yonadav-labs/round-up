from django import template
from django.conf import settings

from six.moves.urllib.parse import urlparse


register = template.Library()

def get_relative_url(absolute_uri):
    return urlparse(absolute_uri).path


def split_url_parts_as_list(relative_url):
    parts_list = relative_url.split("/")
    for part in parts_list:
        if part.strip() == "":
            parts_list.remove(part)

    if len(parts_list) <= 0:
        return None

    return parts_list


def verify_referall_url(netloc):
    if netloc in settings.APP_BASE_URL:
        return True
    else:
        return False


@register.filter(name='determine_return_url')
def determine_return_url(referer, default_return_url):
    if referer and verify_referall_url(urlparse(referer).netloc):
        return get_relative_url(referer)
    else:
        return default_return_url