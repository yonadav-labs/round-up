from decimal import Decimal

from django.core.mail import EmailMessage
from django.db.models import Sum
from django.db.models.signals import post_save
from django.template.loader import render_to_string
from django.utils import timezone
from djmoney.money import Money
from pinax.stripe.actions.subscriptions import update
from pinax.stripe.models import Subscription, Invoice, Plan
import pytz
from django.db import transaction, IntegrityError, connection
from pinax.stripe.signals import WEBHOOK_SIGNALS

from main_app.helpers.external_helpers.fixer_helper import Fixer
from main_app.helpers.external_helpers.stripe_helper import create_invoice_item, get_time_bound, \
    create_invoice_item_description
from main_app.models import AuthAppShopUser, UserProfile, RoundUpOrders, InvoiceCharityLink
from main_app.tasks import sync_store_orders, update_shop_task, product_delete_task, product_update_task, \
    app_uninstall_task, check_user_onboarding_progress, ask_for_review
from source.lib import shopify
from source.lib.pyactiveresource.connection import UnauthorizedAccess, ClientError
from source.lib.shopify.resources.shop import Shop

__author__ = 'JLCJ'
import logging
from django.conf import settings
from source.lib.shopify_webhook.signals import products_update, products_create, products_delete, shop_update, app_uninstalled
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver
from .. import models

"""

This module is used handle incoming Shopify webhooks.

"""

###############################
# Deferred callables
###############################

###############################
# Signal Receivers
###############################

@receiver(shop_update)
def shop_update_webhook_receiver(sender, data, **kwargs):
    update_shop_task.delay(data=data, domain=kwargs['domain'], uid=kwargs['uid'], topic=kwargs['topic'])


@receiver(app_uninstalled)
def app_uninstall_webhook_receiver(sender, data, **kwargs):
    app_uninstall_task.delay(data=data, domain=kwargs['domain'], uid=kwargs['uid'], topic=kwargs['topic'])


@receiver(products_update)
def product_update_webhook_receiver(sender, data, **kwargs):
    product_update_task.delay(data=data, domain=kwargs['domain'], uid=kwargs['uid'], topic=kwargs['topic'])


@receiver(products_create)
def product_created_webhook_receiver(sender, data, **kwargs):
    product_update_task.delay(data=data, domain=kwargs['domain'], uid=kwargs['uid'], topic=kwargs['topic'])


@receiver(products_delete)
def product_deleted_webhook_receiver(sender, data, **kwargs):
    product_delete_task.delay(data=data, domain=kwargs['domain'], uid=kwargs['uid'], topic=kwargs['topic'])


@receiver(post_save, sender=AuthAppShopUser)
def create_profile_handler(sender, instance, created, **kwargs):
    # If the user is not newly created.
    if not created:

        # If timezones have been set then let webhooks worry about changes.
        profile = UserProfile.objects.get(user=instance)
        if not profile.display_timezone and not profile.iana_timezone:
            try:
                with shopify.Session.temp(instance.myshopify_domain, instance.token):
                    shop_details = Shop.current()
                    profile.name = shop_details.name
                    profile.display_timezone = shop_details.timezone
                    profile.iana_timezone = shop_details.iana_timezone
                    profile.shop_contact_email = shop_details.email
                    profile.save()
            except UnauthorizedAccess:
                pass

        if not profile.welcome_email_sent and profile.shop_contact_email:

            contact_name = ''
            contact_phone = ''
            try:
                with shopify.Session.temp(instance.myshopify_domain, instance.token):
                    shop_details = Shop.current()
                    contact_name = shop_details.shop_owner
                    contact_phone = shop_details.phone

            except (UnauthorizedAccess, ClientError):
                pass

            # Send an email to the user to welcome them
            ctx = {
                        "myshopify_domain": instance.myshopify_domain,
                        "contact_name": contact_name
            }
            subject = render_to_string("main_app/email/welcome_subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("main_app/email/welcome_body.txt", ctx)

            email = profile.shop_contact_email

            num_sent = EmailMessage(
                subject,
                message,
                to=[email],
                from_email=settings.PINAX_STRIPE_INVOICE_FROM_EMAIL
            ).send()


            ctx = {
                        "myshopify_domain": instance.myshopify_domain,
                        "datetime_installed": profile.created.strftime('%d, %b %Y %H:%M'),
                        "contact_name": contact_name,
                        "contact_phone": contact_phone,
                        "store_name": profile.name,
                        "email_address": profile.shop_contact_email
            }
            subject = render_to_string("main_app/email/notification_new_user_subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("main_app/email/notification_new_user_body.txt", ctx)

            email = 'shopifyroundup@gmail.com'

            num_sent = EmailMessage(
                subject,
                message,
                to=[email],
                from_email=settings.PINAX_STRIPE_INVOICE_FROM_EMAIL
            ).send()

            check_user_onboarding_progress.apply_async(kwargs={'domain':instance.myshopify_domain}, countdown=86400)
            ask_for_review.apply_async(kwargs={'domain':instance.myshopify_domain}, countdown=1036800)

            profile.welcome_email_sent = True
            profile.save()

        return

    # Create the profile object, only if it is newly created
    profile = UserProfile(user=instance)
    profile.save()



@receiver(WEBHOOK_SIGNALS["invoice.created"])
def handle_invoice_created(sender, event, **kwargs):
    # When Stripe automatically generates an invoice for a recurring payment, your site is notified via webhooks
    # (an invoice.created event). Stripe waits approximately an hour before attempting to pay that invoice. In that
    # time, you can add invoice items to the recently-created invoice so that the forthcoming payment covers it. Be
    # certain to provide the invoice parameter, though, or else the invoice item is added to the next invoice.

    # Any API call that results in a new subscription, such as upgrading or downgrading the plan, also creates a new
    # invoice that is closed from the onset.

    # With a closed invoice, you cannot add invoice items or make other modifications that affect the amount due.
    # (You can still add invoice items to the customer, however, which apply to the next invoice.)

    if event.message['data']['object']['closed']:
        # If the invoice is closed we cannot amend it.
        return

    try:
        subscription = Subscription.objects.get(customer=event.customer, stripe_id=
        event.message['data']['object']['subscription'])
    except (ObjectDoesNotExist, KeyError) as e:
        raise e

    try:
        invoice = Invoice.objects.get(customer=event.customer, stripe_id=event.message['data']['object']['id'])
    except (ObjectDoesNotExist, KeyError) as e:
        raise e

    store = event.customer.user
    if not store:
        raise ObjectDoesNotExist(message='Event: {1} had no associated customer'.format(str(event)))

    utc_dt_period_end, local_dt_period_end = get_time_bound(store, event.message['data']['object']['period_end'])

    if store.userprofile.latest_stripe_billing_period_end_time:
        utc_dt_period_start, local_dt_period_start = get_time_bound(store, event.message['data']['object']['period_start'])
    elif not store.userprofile.latest_stripe_billing_period_end_time:
        utc_dt_period_start = store.userprofile.created
        local_dt_period_start = utc_dt_period_start.astimezone(
                        pytz.timezone(store.userprofile.iana_timezone))

    number_of_days_in_period = (local_dt_period_end - local_dt_period_start).days

    # Check if the app is missing any orders from Shopify.
    if not store.userprofile.latest_order_sync_time or \
        store.userprofile.latest_order_sync_time < utc_dt_period_start:
        sync_store_orders(specific_store=store)

    try:
        round_up_total = [
                Money(data['order_roundup_total__sum'], data['order_roundup_total_currency']) for data in
                RoundUpOrders.objects.exclude(
                    shopify_payment_status=RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED).filter(
                    store=store, state=RoundUpOrders.STATE.PENDING, shopify_created_at__lt=utc_dt_period_end).values(
                    'order_roundup_total_currency').annotate(Sum('order_roundup_total')).order_by()
            ]
        round_up_total = round_up_total[0]
    except IndexError:
        round_up_total = Money(Decimal(0), settings.DEFAULT_CURRENCY)
    except KeyError as e:
        logging.error(str(e.message))
        raise e

    # Get round up count
    round_up_count = RoundUpOrders.objects.exclude(
                    shopify_payment_status=RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED).filter(
                    store=store, state=RoundUpOrders.STATE.PENDING, shopify_created_at__lt=utc_dt_period_end).count()

    if str(round_up_total.currency) != settings.DEFAULT_CURRENCY:
        exchange = Fixer(base=str(round_up_total.currency), symbols=[settings.DEFAULT_CURRENCY])
        response = exchange.convert()
        round_up_total_USD = Money(Decimal(round_up_total.amount *
                                           Decimal(response['rates'][settings.DEFAULT_CURRENCY])),
                                   settings.DEFAULT_CURRENCY)
    else:
        round_up_total_USD = round_up_total

    round_up_orders = RoundUpOrders.objects.filter(
                    store=store, state=RoundUpOrders.STATE.PENDING, shopify_created_at__lt=utc_dt_period_end)

    with transaction.atomic():

        # Update the context orders into the stripe transfer state.
        for order in round_up_orders:
            order.state = RoundUpOrders.STATE.PROCESSING_STRIPE_TRANSFER
            order.save()

    if subscription.plan.stripe_id == settings.PINAX_STRIPE_DEFAULT_PLAN:

        # If the round up total in billing period check is less than $10 USD
        if round_up_total_USD.amount < Money(10.0, settings.DEFAULT_CURRENCY).amount and \
                        round_up_total_USD.amount > Money(0.0, settings.DEFAULT_CURRENCY).amount:

            description = create_invoice_item_description("Minimum donation of $10 USD. ", local_dt_period_start,
                                            local_dt_period_end, round_up_count, round_up_total, round_up_total_USD)

            create_invoice_item(event.customer, subscription, Decimal(10),
                                         settings.DEFAULT_CURRENCY, description, metadata=None,
                                         invoice=invoice)

            store.stripe_sub_reason.pass_low_compliance()

        elif round_up_total_USD.amount >= Money(10.0, settings.DEFAULT_CURRENCY).amount:

            description = create_invoice_item_description(None, local_dt_period_start,
                                            local_dt_period_end, round_up_count, round_up_total, round_up_total_USD)

            create_invoice_item(event.customer, subscription, round_up_total_USD.amount,
                                         settings.DEFAULT_CURRENCY, description, metadata=None,
                                         invoice=invoice)

            # If the daily average during the time period is over 10 USD per day
            if (round_up_total_USD.amount / Decimal(number_of_days_in_period)) >= 10.0:
                store.stripe_sub_reason.fail_low_compliance()

                if not store.stripe_sub_reason.in_compliance() and not store.stripe_sub_reason.plan_locked:
                    high_plan = Plan.objects.get(stripe_id=settings.PINAX_STRIPE_HIGH_VOLUME_PLAN)
                    update(subscription, plan=high_plan, prorate=False)
                    # Clear subscription reason
                    models.StripeCustomerSubReason.objects.update_or_create(
                        store=store, defaults={"subscription": subscription, 'reason': "On {0} moved from the low usage plan to the high usage plan as low compliance failed 3 billing periods in a row.".format(str(timezone.now()))}
                    )

        elif round_up_total_USD.amount == Money(0.0, settings.DEFAULT_CURRENCY).amount:

            store.stripe_sub_reason.pass_low_compliance()

            description = create_invoice_item_description("No donations during period - minimum charge applied. ",
                                                          local_dt_period_start,
                                            local_dt_period_end, round_up_count, round_up_total, round_up_total_USD)

            create_invoice_item(event.customer, subscription, Decimal(3.99),
                                         settings.DEFAULT_CURRENCY, description, metadata=None,
                                         invoice=invoice)
        else:
            raise NotImplementedError("A logical state that was not expected occurred during low plan.")

    elif subscription.plan.stripe_id == settings.PINAX_STRIPE_HIGH_VOLUME_PLAN:

        if round_up_total_USD.amount < Money(10.0, settings.DEFAULT_CURRENCY).amount and \
                        round_up_total_USD.amount > Money(3.99, settings.DEFAULT_CURRENCY).amount:
            store.stripe_sub_reason.fail_high_compliance()

            description = create_invoice_item_description(None, local_dt_period_start,
                                            local_dt_period_end, round_up_count, round_up_total, round_up_total_USD)

            create_invoice_item(event.customer, subscription, round_up_total_USD.amount,
                                         settings.DEFAULT_CURRENCY, description, metadata=None,
                                         invoice=invoice)

            if not store.stripe_sub_reason.in_compliance() and not store.stripe_sub_reason.plan_locked:
                low_plan = Plan.objects.get(stripe_id=settings.PINAX_STRIPE_DEFAULT_PLAN)
                update(subscription, plan=low_plan, prorate=False)
                models.StripeCustomerSubReason.objects.update_or_create(
                        store=store, defaults={"subscription": subscription, 'reason': "On {0} moved from the high usage plan to the low usage plan as high compliance failed 3 billing periods in a row.".format(str(timezone.now()))}
                    )
        elif round_up_total_USD.amount <= Money(3.99, settings.DEFAULT_CURRENCY).amount and \
                        round_up_total_USD.amount >= Money(0.0, settings.DEFAULT_CURRENCY).amount:
            store.stripe_sub_reason.fail_high_compliance()

            description = create_invoice_item_description("Minimum donation of $3.99 USD. ", local_dt_period_start,
                                            local_dt_period_end, round_up_count, round_up_total, round_up_total_USD)

            create_invoice_item(event.customer, subscription, Decimal(3.99),
                                         settings.DEFAULT_CURRENCY, description, metadata=None,
                                         invoice=invoice)

            if not store.stripe_sub_reason.in_compliance():
                low_plan = Plan.objects.get(stripe_id=settings.PINAX_STRIPE_DEFAULT_PLAN)
                update(subscription, plan=low_plan, prorate=False)
        elif round_up_total_USD.amount >= Money(10.0, settings.DEFAULT_CURRENCY).amount:
            store.stripe_sub_reason.pass_high_compliance()

            description = create_invoice_item_description(None, local_dt_period_start,
                                            local_dt_period_end, round_up_count, round_up_total, round_up_total_USD)

            create_invoice_item(event.customer, subscription, round_up_total_USD.amount,
                                         settings.DEFAULT_CURRENCY, description, metadata=None,
                                         invoice=invoice)
        else:
            raise NotImplementedError("A logical state that was not expected occurred during high plan.")

    else:
        raise ValueError("An unknown subscription plan was in an incoming event, Event: {0}".format(str(event)))

    # Link the round up orders to the current event invoice
    with transaction.atomic():
        for order in round_up_orders:
            order.stripe_invoice = invoice
            order.save()

    # Link the current event invoice to the current payment (if it doesn't already exist)
    try:
        # Get current charity
        try:
            charity = store.store_charity.selected_charity
        except ObjectDoesNotExist:
            charity = None

        InvoiceCharityLink.objects.create(
                store=store, invoice=invoice, mapped_charity=charity)
    except IntegrityError:
        pass

    # update the last billing period
    store.userprofile.latest_stripe_billing_period_end_time = utc_dt_period_end
    store.userprofile.save()

    connection.close()
    return


@receiver(WEBHOOK_SIGNALS["invoice.payment_failed"])
def handle_invoice_payment_failure(sender, event, **kwargs):
    try:
        invoice = Invoice.objects.get(customer=event.customer, stripe_id=event.message['data']['object']['id'])
    except (ObjectDoesNotExist, KeyError) as e:
        raise e

    store = event.customer.user
    if not store:
        raise ObjectDoesNotExist(message='Event: {1} had no associated cusomter'.format(str(event)))

    round_up_orders = RoundUpOrders.objects.filter(
                    store=store, state__in=[RoundUpOrders.STATE.PROCESSING_STRIPE_TRANSFER], stripe_invoice=invoice)

    with transaction.atomic():

        # Update the context orders into the stripe transfer state.
        for order in round_up_orders:
            order.state = RoundUpOrders.STATE.FAILED
            order.save()

    connection.close()


@receiver(WEBHOOK_SIGNALS["invoice.payment_succeeded"])
def handle_invoice_payment_succeeded(sender, event, **kwargs):
    try:
        invoice = Invoice.objects.get(customer=event.customer, stripe_id=event.message['data']['object']['id'])
    except (ObjectDoesNotExist, KeyError) as e:
        raise e

    store = event.customer.user
    if not store:
        raise ObjectDoesNotExist(message='Event: {1} had no associated cusomter'.format(str(event)))

    round_up_orders = RoundUpOrders.objects.filter(
                    store=store, state__in=[RoundUpOrders.STATE.PROCESSING_STRIPE_TRANSFER,
                                            RoundUpOrders.STATE.FAILED], stripe_invoice=invoice)

    with transaction.atomic():

        # Update the context orders into the stripe transfer state.
        for order in round_up_orders:
            order.state = RoundUpOrders.STATE.TRANSFERRED
            order.save()

    connection.close()
