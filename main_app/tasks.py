from decimal import Decimal
import logging
import math

from celery import shared_task
from celery.schedules import crontab
from celery.task import periodic_task
from dateutil import parser
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.db import transaction, IntegrityError, connection
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from djmoney.money import Money
from pinax.stripe.actions import subscriptions
from pinax.stripe.actions.customers import get_customer_for_user
from pinax.stripe.actions.sources import delete_card
from pinax.stripe.models import Card
import pytz
from stripe import StripeError

from main_app import models
from main_app.helpers.external_helpers.shopify_webhook_controller import get_return_fields
from main_app.helpers.helpers import create_or_assert_round_up_product
from main_app.models import AuthAppShopUser, RoundUpOrders
from source.lib import shopify
from source.lib.pyactiveresource.connection import UnauthorizedAccess, ClientError
from source.lib.shopify.resources.order import Order
from source.lib.shopify.resources.product import Product
from source.lib import shopify
from source.lib.shopify.resources.webhook import Webhook


@periodic_task(run_every=(crontab(minute=0, hour=0)), name="main_app.tasks.sync_store_orders", ignore_result=True)
def sync_store_orders(specific_store=None):

    user_list = []
    if not specific_store:
        user_list = AuthAppShopUser.objects.filter().exclude(token='00000000000000000000000000000000')
    if specific_store:
        user_list = [specific_store]

    for user in user_list:

        try:

            if not user.userprofile.setup_required:

                with shopify.Session.temp(user.myshopify_domain, user.token):

                    # Track sync times from DB (in UTC)
                    try:
                        current_max_created_UTC = user.userprofile.latest_order_sync_time
                    except ObjectDoesNotExist:
                        logging.error("USER-{0}-GET-ORDERS-NO-PROFILE".format(str(user)))
                        continue

                    new_max_created_UTC = timezone.now()

                    try:
                        round_up_variant_id = user.userprofile.round_up_variant_id
                        if not round_up_variant_id:
                            raise ValueError
                    except ValueError:
                        logging.error("USER-{0}-GET-ORDERS-NO-ROUND-UP-PRODUCT".format(str(user)))
                        continue

                    # Create an empty list to hold incoming orders
                    new_order_list = []

                    # Set query options for Shopify find orders
                    if current_max_created_UTC:
                        # Convert start and end times into store's local timezone.
                        created_at_min = current_max_created_UTC.astimezone(
                            pytz.timezone(user.userprofile.iana_timezone))

                    elif not current_max_created_UTC:
                        # Only look back as far as the user has existed.
                        created_at_min = user.userprofile.created.astimezone(
                            pytz.timezone(user.userprofile.iana_timezone))

                    created_at_max = new_max_created_UTC.astimezone(
                            pytz.timezone(user.userprofile.iana_timezone))

                    order_args = {'status': "any",
                              'created_at_min': created_at_min,
                              'created_at_max': created_at_max}

                    # Iterate through Shopify orders for store
                    orders_count = Order.count(**order_args)
                    limit_per_page = 50
                    pages = math.ceil(orders_count / limit_per_page)

                    # Iterate through all API Pages.
                    for i in range(1, int(pages) + 2):
                        orders = Order.find(limit=limit_per_page, page=i, **order_args)

                        # Iterate through the current page of Shopify orders to find line items that contain round up products.
                        for order in orders:
                            round_up_line_item_id = None
                            new_order = None

                            if not order.cancel_reason and order.financial_status in ('paid', 'partially_refunded',
                                                                                      'partially_paid', 'refunded'):

                                for item in order.line_items:

                                    if item.variant_id == round_up_variant_id:

                                        # Create a Round Up Order Product
                                        new_order = RoundUpOrders(store=user,
                                                                  order_number=order.id,
                                                                  order_name=order.name,
                                                                  order_total=Money(Decimal(order.total_price), order.currency),
                                                                  order_roundup_total=Money((Decimal(item.price) * item.quantity) - Decimal(item.total_discount), order.currency),
                                                                  shopify_created_at=parser.parse(order.created_at).astimezone(pytz.utc)
                                                                  )

                                        new_order_list.append(new_order)
                                        round_up_line_item_id = item.id

                                        break

                                if round_up_line_item_id and new_order:

                                    # Check if the round up item is refunded for this order.
                                    for refund in order.refunds:

                                        for refund_line_item in refund.refund_line_items:
                                            if refund_line_item.line_item_id == round_up_line_item_id:
                                                new_order.order_roundup_total = new_order.order_roundup_total - Money((refund_line_item.quantity * settings.ROUND_UP_DEFAULT_PRICE), order.currency)

                                                new_order.shopify_payment_status = RoundUpOrders.SHOPIFY_PAYMENT_STATUS.PARTIALLY_REFUNDED

                                                if new_order.order_roundup_total <= Money(Decimal(0), order.currency):
                                                    new_order.order_roundup_total = Money(Decimal(0), order.currency)
                                                    new_order.shopify_payment_status = \
                                                        RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED

                    try:
                        with transaction.atomic():
                            if new_order_list:
                                RoundUpOrders.objects.bulk_create(new_order_list)

                            if new_max_created_UTC:
                                user.userprofile.latest_order_sync_time = new_max_created_UTC
                                user.userprofile.save()
                    except IntegrityError:
                        # Try to process orders individually
                        for new_order in new_order_list:
                            try:
                                new_order.save()
                            except IntegrityError:
                                pass

                        if new_max_created_UTC:
                            user.userprofile.latest_order_sync_time = new_max_created_UTC
                            user.userprofile.save()

        except Exception as e:
            logging.error(e.message)
            pass


@shared_task
def check_user_onboarding_progress(domain):
    try:
        store = models.AuthAppShopUser.objects.get(myshopify_domain=domain)
    except ObjectDoesNotExist:
        logging.warning("Onboarding-Check-Task-No-User: " + str(domain))
        return

    if not store.userprofile.onboarding_email_sent:

        required_steps_string = ''

        if store.userprofile.setup_required:
            # User has to do all setup tasks
            required_steps_string = '- Please complete the Round Up App setup wizard by accessing the app from your Shopify admin.\n'

        # Does the customer have a stripe cusomter?
        stripe_customer = get_customer_for_user(store)
        # Get all the current customers/stores payment methods
        cards = Card.objects.filter(customer=stripe_customer).order_by("created_at")

        if not stripe_customer or not cards:
            required_steps_string = '- Please add your payment information to the Round Up App payment settings (Required to make donations).\n'

        # Does the customer have a charity selected?
        try:
            if not store.store_charity.selected_charity:
                required_steps_string = '- Please select a Charity in the Round Up app.\n'
        except ObjectDoesNotExist:
            required_steps_string = '- Please select a Charity in the Round Up app.\n'

        # Has the customer signalled that they have included the setup stuff?
        try:
            if not store.userprofile.install_user_verified:
                required_steps_string = '- Please ensure that you have modified your Cart page theme to include the Round Up app code snippet.\n'
        except ObjectDoesNotExist:
            required_steps_string = '- Please ensure that you have modified your Cart page theme to include the Round Up app code snippet.\n'

        if required_steps_string != '':

            # Send an email
            ctx = {
                "myshopify_domain": store.myshopify_domain,
                "required_steps_string": required_steps_string
            }
            subject = render_to_string("main_app/email/required_steps_subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("main_app/email/required_steps_body.txt", ctx)

            email = store.userprofile.shop_contact_email

            num_sent = EmailMessage(
                subject,
                message,
                to=[email],
                from_email=settings.PINAX_STRIPE_INVOICE_FROM_EMAIL
            ).send()

            store.userprofile.onboarding_email_sent = True
            store.userprofile.save()

            return

    else:
        return


@shared_task
def ask_for_review(domain):
    try:
        store = models.AuthAppShopUser.objects.get(myshopify_domain=domain)
    except ObjectDoesNotExist:
        logging.warning("Review-Check-Task-No-User: " + str(domain))
        return

    if not store.token or store.token == '00000000000000000000000000000000':
        return

    if not store.userprofile.review_email_sent:

        # Does the customer have a stripe cusomter?
        stripe_customer = get_customer_for_user(store)
        # Get all the current customers/stores payment methods
        cards = Card.objects.filter(customer=stripe_customer).order_by("created_at")

        if store.userprofile.setup_required == False and stripe_customer and cards:

            # Send an email
            ctx = {
                "myshopify_domain": store.myshopify_domain,
            }
            subject = render_to_string("main_app/email/review_subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("main_app/email/review_body.txt", ctx)

            email = store.userprofile.shop_contact_email

            num_sent = EmailMessage(
                subject,
                message,
                to=[email],
                from_email=settings.PINAX_STRIPE_INVOICE_FROM_EMAIL
            ).send()

            store.userprofile.review_email_sent = True
            store.userprofile.save()

            return

    else:
        return


@shared_task
def app_uninstall_task(data, **kwargs):
    try:
        user = models.AuthAppShopUser.objects.get(myshopify_domain=kwargs['domain'])

        user.token = '00000000000000000000000000000000'
        user.save()

        # Cancel any Stripe subscriptions
        try:
            stripe_customer = get_customer_for_user(user)
            if subscriptions.has_active_subscription(stripe_customer):
                user_subscriptions = models.Subscription.objects.filter(
                    customer=stripe_customer
                ).filter(
                    Q(ended_at__isnull=True) | Q(ended_at__gt=timezone.now())
                )
                for subscription in user_subscriptions:
                    subscriptions.cancel(subscription, at_period_end=False)

                # Clear subscription reason
                models.StripeCustomerSubReason.objects.update_or_create(
                    store=user, defaults={"subscription": None, 'reason': None}
                )

                # Clear stripe cards
                user_cards = Card.objects.filter(customer=stripe_customer).order_by("created_at")
                for card in user_cards:
                    delete_card(stripe_customer, card.stripe_id)
        except StripeError as e:
            logging.error(str(e.message))

        # Send an email to the user to welcome them
        try:
            ctx = {
                "myshopify_domain": user.myshopify_domain,
            }
            subject = render_to_string("main_app/email/uninstall_subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("main_app/email/uninstall_body.txt", ctx)

            email = user.userprofile.shop_contact_email

            num_sent = EmailMessage(
                subject,
                message,
                to=[email],
                from_email=settings.PINAX_STRIPE_INVOICE_FROM_EMAIL
            ).send()
        except Exception:
            pass

        # Invalidate any existing user sessions.
        user.clear_user_sessions()
        connection.close()

    except ObjectDoesNotExist:
        if kwargs['domain']:
            logging.warning("App-Uninstall-Webhook-No-User-Found:  " + str(kwargs['domain']))
            return
    except Exception as e:
        logging.error("App-Uninstall-Webhook-Unknown-Exception: "+str(e.message))
        raise e


@shared_task
def update_shop_task(data, **kwargs):
    try:
        user = models.AuthAppShopUser.objects.get(myshopify_domain=kwargs['domain'])
    except ObjectDoesNotExist:
        logging.warning("Shop-Update-Webhook-No-User-Found:  " + str(kwargs['domain']))
        connection.close()
        return

    try:
        change_made = False

        if user.userprofile.iana_timezone != data['iana_timezone']:
            user.userprofile.iana_timezone = data['iana_timezone']
            change_made = True
        if user.userprofile.display_timezone != data['timezone']:
            user.userprofile.display_timezone = data['timezone']
            change_made = True

        if user.userprofile.name != data['name']:
            user.userprofile.name = data['name']
            change_made = True

        if user.userprofile.shop_contact_email != data['email']:
            user.userprofile.shop_contact_email = data['email']
            change_made = True

        if change_made:
            user.userprofile.save()

        connection.close()

    except Exception as e:
        logging.error("Shop-Update-Webhook-Unknown-Exception: "+str(e.message))
        raise e


@shared_task
def product_delete_task(data, **kwargs):
    try:
        store = models.AuthAppShopUser.objects.get(myshopify_domain=kwargs['domain'])
    except ObjectDoesNotExist:
        logging.warning("Product-Delete-Webhook-No-User-Found: " + str(kwargs['domain']))
        return

    try:
        # Check if the product deleted is the stores round up product
        if data['id'] == store.userprofile.round_up_product_id:

            # If so, then restore it by creating a new round up product
            create_or_assert_round_up_product(store, deleted=True)

        connection.close()

    except Exception as e:
        logging.error("Product-Delete-Webhook-Unknown-Exception: "+str(e.message))
        raise e


@shared_task
def product_update_task(data, **kwargs):
    try:
        store = models.AuthAppShopUser.objects.get(myshopify_domain=kwargs['domain'])
    except ObjectDoesNotExist:
        logging.warning("Product-Update-Webhook-No-User-Found: " + str(kwargs['domain']))
        return

    try:

        if data['id'] == store.userprofile.round_up_product_id:

            with shopify.Session.temp(store.myshopify_domain, store.token):

                # Compare data to the expected values.
                discrepancy = False

                if len(data['variants']) != 1:
                    discrepancy = True

                try:
                    if data['variants'][0]['price'] != "0.01":
                        discrepancy = True

                    if data['variants'][0]['inventory_management'] != None:
                        discrepancy = True

                    if data['variants'][0]['taxable'] != False:
                        discrepancy = True

                    if data['variants'][0]['requires_shipping'] != False:
                        discrepancy = True
                except KeyError:
                    discrepancy = True

                # If there are discrepencies, destroy the product, and recreate it.
                if discrepancy:
                    product = Product.find(store.userprofile.round_up_product_id)
                    product.destroy()

        connection.close()

    except Exception as e:
        logging.error("Product-Update-Webhook-Unknown-Exception: "+str(e.message))
        raise e


@shared_task(bind=True)
def internal_debug_task(self):
    print(self.request.id)
    print('Request: {0!r}'.format(self.request))


# @shared_task
# def task_create_or_update_webhooks(full_url):
#     """
#     Purpose: This function will create, or ensure that they are created all required application
#     webhooks (shop update, product update/delete, and app uninstall.
#     :param full_url: get the POST url for webhook created from the shopify_webhook module
#     :param user: the authenticated and verified user to create a webhook for
#     :param webhook_topic: what webhook to register
#     :return: true on success, false on fail
#     """
#
#     user_list = AuthAppShopUser.objects.filter().exclude(token='00000000000000000000000000000000')
#
#     for user in user_list:
#
#         # if not user.userprofile.round_up_product_id or not user.userprofile.round_up_js_script_id or not user.userprofile.round_up_variant_id:
#
#             # user = AuthAppShopUser.objects.get(myshopify_domain='the-brave-collection.myshopify.com')
#             try:
#                 with shopify.Session.temp(user.myshopify_domain, user.token):
#                     required_webhook_topics = ["app/uninstalled",
#                                                "shop/update",
#                                                "products/delete",
#                                                "products/update"
#                                                ]
#
#                     # Check to see if the required webhooks exist for the current Shopify shop.
#                     shop_webhooks = Webhook.find()
#
#                     for required_webhook in required_webhook_topics:
#                         webhook_found_and_accurate = False
#
#                         for shopify_webhook in shop_webhooks:
#
#                             expected_fields = get_return_fields(shopify_webhook.topic)
#
#                             # Do the required webhooks exist?
#                             if required_webhook == shopify_webhook.topic:
#                                 if shopify_webhook.format == "json" and shopify_webhook.address == full_url and \
#                                                 shopify_webhook.fields == expected_fields:
#                                         webhook_found_and_accurate = True
#                                         break
#                                 else:
#                                     shopify_webhook.address = full_url
#                                     shopify_webhook.format = "json"
#                                     if expected_fields:
#                                         shopify_webhook.fields = expected_fields
#                                     shopify_webhook.save()
#                                     webhook_found_and_accurate = True
#                                     break
#
#                         if not webhook_found_and_accurate:
#                         # If a webhook does not exist, create it.
#                             new_webhook = Webhook()
#                             new_webhook.topic = required_webhook
#                             new_webhook.address = full_url
#                             new_webhook.format = "json"
#                             expected_fields = get_return_fields(required_webhook)
#                             if expected_fields:
#                                 new_webhook.fields = expected_fields
#                             new_webhook.save()
#
#             except (UnauthorizedAccess, ClientError):
#                 user.token = '00000000000000000000000000000000'
#                 user.save()
#                 continue


def manual_order_sync():
    user_list = []
    specific_store = AuthAppShopUser.objects.get(id=23)
    user_list = [specific_store]

    for user in user_list:

        try:

            if not user.userprofile.setup_required:

                with shopify.Session.temp(user.myshopify_domain, user.token):

                    # Track sync times from DB (in UTC)
                    try:
                        current_max_created_UTC = user.userprofile.latest_order_sync_time
                        print("Current UTC Sync time: " + str(current_max_created_UTC))
                    except ObjectDoesNotExist:
                        logging.error("USER-{0}-GET-ORDERS-NO-PROFILE".format(str(user)))
                        continue

                    new_max_created_UTC = timezone.now()

                    try:
                        round_up_variant_id = user.userprofile.round_up_variant_id
                        print("Round up variant ID: " + str(round_up_variant_id))
                        if not round_up_variant_id:
                            raise ValueError
                    except ValueError:
                        logging.error("USER-{0}-GET-ORDERS-NO-ROUND-UP-PRODUCT".format(str(user)))
                        continue

                    # Create an empty list to hold incoming orders
                    new_order_list = []

                    # Set query options for Shopify find orders
                    if current_max_created_UTC:
                        # Convert start and end times into store's local timezone.
                        created_at_min = current_max_created_UTC.astimezone(
                            pytz.timezone(user.userprofile.iana_timezone))

                    elif not current_max_created_UTC:
                        # Only look back as far as the user has existed.
                        created_at_min = user.userprofile.created.astimezone(
                            pytz.timezone(user.userprofile.iana_timezone))

                    created_at_max = new_max_created_UTC.astimezone(
                            pytz.timezone(user.userprofile.iana_timezone))

                    order_args = {'status': "any",
                              'created_at_min': created_at_min,
                              'created_at_max': created_at_max}

                    # Iterate through Shopify orders for store
                    orders_count = Order.count(**order_args)
                    limit_per_page = 50
                    pages = math.ceil(orders_count / limit_per_page)

                    # Iterate through all API Pages.
                    for i in range(1, int(pages) + 2):
                        orders = Order.find(limit=limit_per_page, page=i, **order_args)

                        # Iterate through the current page of Shopify orders to find line items that contain round up products.
                        for order in orders:
                            round_up_line_item_id = None
                            new_order = None

                            if not order.cancel_reason and order.financial_status in ('paid', 'partially_refunded',
                                                                                      'partially_paid', 'refunded'):

                                for item in order.line_items:

                                    if item.variant_id == round_up_variant_id:

                                        # Create a Round Up Order Product
                                        new_order = RoundUpOrders(store=user,
                                                                  order_number=order.id,
                                                                  order_name=order.name,
                                                                  order_total=Money(Decimal(order.total_price), order.currency),
                                                                  order_roundup_total=Money((Decimal(item.price) * item.quantity) - Decimal(item.total_discount), order.currency),
                                                                  shopify_created_at=parser.parse(order.created_at).astimezone(pytz.utc)
                                                                  )

                                        new_order_list.append(new_order)
                                        round_up_line_item_id = item.id

                                        break

                                if round_up_line_item_id and new_order:

                                    # Check if the round up item is refunded for this order.
                                    for refund in order.refunds:

                                        for refund_line_item in refund.refund_line_items:
                                            if refund_line_item.line_item_id == round_up_line_item_id:
                                                new_order.order_roundup_total = new_order.order_roundup_total - Money((refund_line_item.quantity * settings.ROUND_UP_DEFAULT_PRICE), order.currency)

                                                new_order.shopify_payment_status = RoundUpOrders.SHOPIFY_PAYMENT_STATUS.PARTIALLY_REFUNDED

                                                if new_order.order_roundup_total <= Money(Decimal(0), order.currency):
                                                    new_order.order_roundup_total = Money(Decimal(0), order.currency)
                                                    new_order.shopify_payment_status = \
                                                        RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED

                    try:

                        print("Bulk create new order list: " + str(new_order_list))

                        with transaction.atomic():
                            if new_order_list:
                                RoundUpOrders.objects.bulk_create(new_order_list)

                            if new_max_created_UTC:
                                user.userprofile.latest_order_sync_time = new_max_created_UTC
                                user.userprofile.save()
                    except IntegrityError:
                        print("There was an integrity error")
                        print("Count of new records: " + str(len(new_order_list)))
                        # Try to process orders individually
                        for new_order in new_order_list:
                            try:
                                new_order.save()
                                print("SAVED: Order {0}".format(str(new_order.order_number)))
                            except IntegrityError:
                                print("Order {0} has an integrity error".format(str(new_order.order_number)))
                                pass

                        if new_max_created_UTC:
                            print("Saving the sync date now anyways")
                            user.userprofile.latest_order_sync_time = new_max_created_UTC
                            user.userprofile.save()

        except Exception as e:
            print("There was a generic error: " + str(e.message))
            logging.error(e.message)
            pass