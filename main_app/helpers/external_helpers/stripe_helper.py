from datetime import datetime
import logging

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from pinax.stripe import models, utils
from pinax.stripe.actions import subscriptions
from pinax.stripe.actions.customers import sync_customer
from pinax.stripe.actions.sources import delete_card, create_card
from pinax.stripe.models import Card, Plan
import pytz
import stripe
from pinax.stripe.actions.customers import get_customer_for_user

from main_app.models import StripeCustomerSubReason
from source.lib import shopify
from source.lib.shopify.resources.order import Order


def create_without_account_custom(user, card=None, plan=None, charge_immediately=False, quantity=None):
    cus = models.Customer.objects.filter(user=user).first()
    if cus is not None:
        try:
            stripe.Customer.retrieve(cus.stripe_id)
            return cus
        except stripe.error.InvalidRequestError:
            pass

    # At this point we maybe have a local Customer but no stripe customer
    # let's create one and make the binding
    stripe_customer = stripe.Customer.create(
        email=user.userprofile.shop_contact_email,
        source=card,
        plan=plan,
        quantity=quantity,
        trial_end=None
    )
    cus, created = models.Customer.objects.get_or_create(
        user=user,
        defaults={
            "stripe_id": stripe_customer["id"]
        }
    )
    if not created:
        cus.stripe_id = stripe_customer["id"]  # sync_customer will call cus.save()
    sync_customer(cus, stripe_customer)
    return cus


def process_stripe_user(store, card_token, existing_cards=None):

    # Get the current stores stripe customer info.
    stripe_customer = get_customer_for_user(store)
    # Get all the current customers/stores payment methods
    if not existing_cards:
        existing_cards = Card.objects.filter(customer=stripe_customer).order_by("created_at")

    stripe_card_token = card_token

    # If the store has no stripe customer, create one.
    if not stripe_customer:
        stripe_customer = create_without_account_custom(store, card=stripe_card_token)
    else:
        # Save the new card to the existing user, and delete old cards.
        for card in existing_cards:
            delete_card(stripe_customer, card.stripe_id)

        create_card(stripe_customer, token=stripe_card_token)

    return stripe_customer


def estimate_donation_volume(store):
    with shopify.Session.temp(store.myshopify_domain, store.token):

        # Determine if a store might be "high volume"
        last_week_start_time = timezone.now() - relativedelta(days=7, hours=0, minutes=0, seconds=0, microseconds=0)

        order_args = {'status': "any",
                              'created_at_min': last_week_start_time}

        # Iterate through Shopify orders for store
        last_week_orders_count = Order.count(**order_args)

        chance_of_donation = .40
        average_donation_amount = .30

        order_per_day = last_week_orders_count / 7.0
        per_day_donation_estimation = (order_per_day * chance_of_donation) * average_donation_amount

        if per_day_donation_estimation >= 10.0:
            plan = Plan.objects.get(stripe_id=settings.PINAX_STRIPE_HIGH_VOLUME_PLAN)

            return (plan, "{0} is on 'High Volume' plan because at the time of their enrollment they had "
                                        "(in the previous 7 days) an average of {1} orders per day. We estimated that"
                                        " they would have a donation volume of {2} per day (Greater than 10). ({3}[average orders per day] * "
                                        "{4}[chance_of_donation]) * {5}[average donation amount]".format(
                str(store), str(round(order_per_day,2)), str(round(per_day_donation_estimation,2)),
                str(round(order_per_day,2)), str(chance_of_donation), str(average_donation_amount)
            ))
        else:
            plan = Plan.objects.get(stripe_id=settings.PINAX_STRIPE_DEFAULT_PLAN)

            return (plan, "{0} is on 'Low Volume' plan because at the time of their enrollment they had "
                                        "(in the previous 7 days) an average of {1} orders per day. We estimated that"
                                        " they would have a donation volume of {2} per day (Less than 10). ({3}[average orders per day] * "
                                        "{4}[chance_of_donation]) * {5}[average donation amount]".format(
                str(store), str(round(order_per_day,2)), str(round(per_day_donation_estimation,2)),
                str(round(order_per_day,2)), str(chance_of_donation), str(average_donation_amount)
            ))


def create_stripe_user_subscription(store, stripe_customer=None):

        if not stripe_customer:
            stripe_customer = get_customer_for_user(store)

        if subscriptions.has_active_subscription(stripe_customer):
            return True

        plan, reason = estimate_donation_volume(store)

        subscription = subscriptions.create(stripe_customer, plan)

        StripeCustomerSubReason.objects.update_or_create(
            store=store, defaults={"subscription": subscription, 'reason': reason}
        )

        return True


def create_invoice_item(customer, subscription, amount, currency, description, metadata=None, invoice=None):
     """
     :param customer: The pinax-stripe Customer
     :param invoice:
     :param subscription:
     :param amount:
     :param currency:
     :param description:
     :param metadata: Any optional metadata that is attached to the invoice item
     :return:
     """
     if invoice:
         stripe_invoice_item = stripe.InvoiceItem.create(
             customer=customer.stripe_id,
             amount=utils.convert_amount_for_api(amount, currency),
             currency=currency,
             description=description,
             invoice=invoice.stripe_id,
             metadata=metadata,
             subscription=subscription.stripe_id,
         )
     else:
         stripe_invoice_item = stripe.InvoiceItem.create(
             customer=customer.stripe_id,
             amount=utils.convert_amount_for_api(amount, currency),
             currency=currency,
             description=description,
             metadata=metadata,
             subscription=subscription.stripe_id,
         )


     period_end = utils.convert_tstamp(stripe_invoice_item["period"], "end")
     period_start = utils.convert_tstamp(stripe_invoice_item["period"], "start")

     # We can safely take the plan from the subscription here because we are creating a new invoice item for this new invoice that is applicable
     # to the current subscription/current plan.
     plan = subscription.plan

     defaults = dict(
         amount=utils.convert_amount_for_db(stripe_invoice_item["amount"], stripe_invoice_item["currency"]),
         currency=stripe_invoice_item["currency"],
         proration=stripe_invoice_item["proration"],
         description=description,
         line_type=stripe_invoice_item["object"],
         plan=plan,
         period_start=period_start,
         period_end=period_end,
         quantity=stripe_invoice_item.get("quantity"),
         subscription=subscription,
     )
     inv_item, inv_item_created = invoice.items.get_or_create(
         stripe_id=stripe_invoice_item["id"],
         defaults=defaults
     )
     return utils.update_with_defaults(inv_item, defaults, inv_item_created)


def get_time_bound(store, timestamp):

    utc_dt_period = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)

    try:
        local_dt_period = utc_dt_period.astimezone(
                        pytz.timezone(store.userprofile.iana_timezone))
    except ObjectDoesNotExist as e:
        logging.error(str(e.message))
        raise e

    return utc_dt_period, local_dt_period


def create_invoice_item_description(specific_message, local_start_datetime, local_end_datetime, count, total, total_USD):

    if not specific_message:
        specific_message=""

    return "{0}During period ({1} to {2}) there were {3} donations " \
                              "totalling {4} ({5} 'USD').".format(
                                                            specific_message,
                                                            local_start_datetime.strftime('%Y-%m-%d %H:%M'),
                                                            local_end_datetime.strftime('%Y-%m-%d %H:%M'),
                                                            str(count),
                                                            str(total),
                                                            str(total_USD))




