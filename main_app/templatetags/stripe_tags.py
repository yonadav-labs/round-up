from django import template
from pinax.stripe.actions.customers import get_customer_for_user
from pinax.stripe.actions.subscriptions import has_active_subscription
from pinax.stripe.models import Subscription

register = template.Library()

@register.filter(name='stripe_sub_status')
def stripe_sub_status(store):

    stripe_customer = get_customer_for_user(store)
    active = has_active_subscription(customer=stripe_customer)

    subscription = Subscription.objects.filter(customer=stripe_customer).order_by('-start').first()
    if not subscription:
        plan = "No plan"
    else:
        plan = subscription.plan.name

    if active:
        return "<span class='label label-success'>Stripe: Active - " + str(plan)+ "</span>"
    else:
        return "<span class='label label-default'>Stripe: Inactive - " + str(plan)+ "</span>"