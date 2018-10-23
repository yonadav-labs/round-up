from django import template
from django.utils import timezone
from django.template import defaultfilters

register = template.Library()

@register.filter(expects_localtime=True, is_safe=False, name='get_order_date')
def get_order_date(shopify_date_str_lctz):
    if not shopify_date_str_lctz:
        return 'date unknown'

    try:
        delta = shopify_date_str_lctz.date() - timezone.localtime(timezone.now()).date()

        # If time within 60 minutes send time back
        if delta.days == 0:
            seconds_delta = abs(int((shopify_date_str_lctz - timezone.localtime(timezone.now())).total_seconds()))
            minute_delta = seconds_delta / 60

            # Check if within the hour
            if seconds_delta < 60:
                return str(seconds_delta) + " second" + defaultfilters.pluralize(seconds_delta) + " ago"
            elif minute_delta in range(1, 59):
                return str(minute_delta) + " minute" + defaultfilters.pluralize(minute_delta) + " ago"
            else:
                return defaultfilters.date(shopify_date_str_lctz, "g:ia")
        # If time was yesterday
        elif delta.days == -1:
            return "Yesterday, " + defaultfilters.date(shopify_date_str_lctz, "g:ia")
        elif delta.days in range(-7, -2):
            return defaultfilters.date(shopify_date_str_lctz, "l, g:ia")
        elif delta.days in range(-365, -8):
            return defaultfilters.date(shopify_date_str_lctz, "M j, g:ia")
        else:
            return defaultfilters.date(shopify_date_str_lctz, "M j Y, g:ia")
    except Exception as e:
        return 'date unknown'