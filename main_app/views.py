from __future__ import print_function
from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.db import connection
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django_tables2 import RequestConfig
from django_tables2.export import TableExport
from djmoney.money import Money
from pinax.stripe.actions import customers, charges, invoices
from pinax.stripe.actions.customers import get_customer_for_user
from pinax.stripe.actions.subscriptions import update
from pinax.stripe.models import Card, Subscription, Invoice, Plan, Customer
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required as default_login_required
import pytz
from stripe import InvalidRequestError
from main_app.filters import StoreFilter, CharityFilter, InvoiceFilter
from main_app.forms import StoreFilterFormHelper, CharityFilterFormHelper, TransferFilterFormHelper
from main_app.helpers.external_helpers.fixer_helper import Fixer
from main_app.helpers.external_helpers.shopify_webhook_controller import create_or_update_webhooks
from main_app.helpers.external_helpers.stripe_helper import process_stripe_user, \
    create_stripe_user_subscription, get_time_bound
from main_app.helpers.helpers import create_or_assert_round_up_product, create_or_assert_round_up_asset
from main_app.models import StoreCharityHistory, AuthAppShopUser, RoundUpOrders, Charities, UserProfile, \
    InvoiceCharityLink
from main_app.tables import StoreTable, RoundUpTable, InvoiceTable, CharityTable, AllInvoiceTable, CustomerRoundUpTable, \
    CustomerInvoiceTable
from main_app.tasks import manual_order_sync
from source.lib.pyactiveresource.connection import ResourceNotFound, UnauthorizedAccess, ClientError
from source.lib.shopify.resources.shop import Shop
from source.lib.shopify_auth.decorators import login_required, token_update_required, url_kwargs_match_request_user, \
    setup_required
from . import models
import source.lib.shopify as shopify
from . import forms


####################################
# View Definition Starts
####################################
from source.lib.shopify_webhook.decorators import app_proxy


@login_required
@url_kwargs_match_request_user
@token_update_required
def onboarding_wizard(request, *args, **kwargs):
    with request.user.session:
        template = "main_app/onboarding.html"

        if not request.user.userprofile.setup_required:
            return redirect('main_app:transaction_list', store_url=request.user.store_url_str())

        try:
            charity_instance = request.user.store_charity
        except ObjectDoesNotExist:
            charity_instance = StoreCharityHistory(store=request.user)

        STRIPE_PUBLIC_KEY = settings.PINAX_STRIPE_PUBLIC_KEY

        # Get all current global charities
        all_charities = Charities.objects.exclude(charity_logo='').order_by('name')

        if request.method == "POST":

            stripe_customer = process_stripe_user(request.user, request.POST.get('stripeToken', None))

            if stripe_customer:
                create_stripe_user_subscription(store=request.user, stripe_customer=stripe_customer)
                request.user.userprofile.setup_required = False
                request.user.userprofile.save()

                messages.success(request, "The payment method was set.")
                return redirect('main_app:transaction_list', store_url=request.user.store_url_str())
            else:
                messages.error(request, "There was an issue with your payment method.")

        return render(request, template, {'all_charities': all_charities,
                                              'charity_instance': charity_instance, 'STRIPE_PUBLIC_KEY': STRIPE_PUBLIC_KEY})


@login_required
@url_kwargs_match_request_user
@token_update_required
@setup_required
def tutorial(request, *args, **kwargs):
    with request.user.session:

        active_charity_count = Charities.objects.exclude(charity_logo='').count()

        return render(request, "main_app/tutorial.html", {'active_charity_count': active_charity_count})


@login_required
@url_kwargs_match_request_user
@token_update_required
@setup_required
def charity_selection(request, *args, **kwargs):
    with request.user.session:
        template = "main_app/charities.html"

        try:
            charity_instance = request.user.store_charity
        except ObjectDoesNotExist:
            charity_instance = StoreCharityHistory(store=request.user)

        # Get all current global charities
        all_charities = Charities.objects.exclude(charity_logo='').order_by('name')

        return render(request, template, {'all_charities': all_charities,
                                              'charity_instance': charity_instance})


@login_required
@url_kwargs_match_request_user
@token_update_required
def contact(request, *args, **kwargs):
    with request.user.session:
        template = "main_app/contact.html"

        if request.method == "POST":
            contact_form = forms.ContactForm(request.POST)

            if not contact_form.is_valid():
                return render(request, template, {"contact_form":contact_form})

            if contact_form.is_valid():

                try:
                    email = request.user.userprofile.shop_contact_email
                except ObjectDoesNotExist:
                    email = settings.PINAX_STRIPE_INVOICE_FROM_EMAIL

                ctx = {
                    "myshopify_domain": request.user.myshopify_domain,
                    "message": str(contact_form.cleaned_data['message']),
                    "phone_number": str(contact_form.cleaned_data.get('phone_number', None)),
                    "full_name": str(contact_form.cleaned_data.get('full_name', None)),
                    "customer_email": str(email)
                }
                subject = render_to_string("main_app/email/contact_subject.txt", ctx)
                subject = subject.strip()
                message = render_to_string("main_app/email/contact_body.txt", ctx)

                EmailMessage(
                    subject,
                    message,
                    to=[settings.HELP_TO_MAILBOX_EMAIL],
                    reply_to=[email],
                    from_email=settings.PINAX_STRIPE_INVOICE_FROM_EMAIL,
                ).send()

                messages.success(request, "Your support message was sent.")
                return redirect('main_app:home_page', store_url=request.user.store_url_str())

        else:
            contact_form = forms.ContactForm()

            return render(request, template, {"contact_form":contact_form})

        return render(request, template,)


@login_required
@url_kwargs_match_request_user
@token_update_required
def about(request, *args, **kwargs):
    with request.user.session:
        return render(request, "main_app/about.html",)


@login_required
@url_kwargs_match_request_user
@token_update_required
@setup_required
def payment_information(request, *args, **kwargs):

    with request.user.session:

        # Get the current stores stripe customer info.
        stripe_customer = get_customer_for_user(request.user)
        # Get all the current customers/stores payment methods
        cards = Card.objects.filter(customer=stripe_customer).order_by("created_at")

        STRIPE_PUBLIC_KEY = settings.PINAX_STRIPE_PUBLIC_KEY

        if request.method == "POST":

            stripe_customer = process_stripe_user(request.user, request.POST.get('stripeToken', None), existing_cards=cards)
            create_stripe_user_subscription(store=request.user, stripe_customer=stripe_customer)

            messages.success(request, "The payment method was changed.")
            return redirect('main_app:payment_information', store_url=request.user.store_url_str())

        return render(request, "main_app/payment_information.html", {'cards':cards, 'STRIPE_PUBLIC_KEY': STRIPE_PUBLIC_KEY} )


@login_required
@url_kwargs_match_request_user
@token_update_required
@setup_required
def order_list(request, *args, **kwargs):

    with request.user.session:
        template = "main_app/order_list.html"

        # Get dashboard details
        round_up_count = RoundUpOrders.objects.exclude(
            shopify_payment_status=RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED).filter(store=request.user).count()

        round_up_total = [
            Money(data['order_roundup_total__sum'], data['order_roundup_total_currency']) for data in
            RoundUpOrders.objects.exclude(
            shopify_payment_status=RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED).filter(store=request.user).values(
                'order_roundup_total_currency').annotate(Sum('order_roundup_total')).order_by()
        ]

        if round_up_total and len(round_up_total) == 1:
            round_up_total = round_up_total[0]
        else:
            round_up_total = Money(0.0, settings.DEFAULT_CURRENCY)

        table = CustomerRoundUpTable(RoundUpOrders.objects.filter(store=request.user).order_by('-shopify_created_at'))

        RequestConfig(request, paginate={'per_page': 50}).configure(table)

        return render(request, template, {
            'table': table,
            'round_up_count': round_up_count,
            'round_up_total': round_up_total
        })


@login_required
@url_kwargs_match_request_user
@token_update_required
@setup_required
def invoice_list(request, *args, **kwargs):

    with request.user.session:

        template = "main_app/invoice_list.html"

        stripe_customer = get_customer_for_user(request.user)

        table = CustomerInvoiceTable(Invoice.objects.filter(customer=stripe_customer).order_by('date'))

        RequestConfig(request, paginate={'per_page': 50}).configure(table)

        return render(request, template, {
            'table': table,
        })


@login_required
@token_update_required
def login_redirect(request, *args, **kwargs):
    try:
        if request.user.adminprofile.is_admin:
            return redirect("main_app:admin_store_list")
    except ObjectDoesNotExist:
            pass

    with request.user.session:
        return redirect("main_app:transaction_list", store_url=request.user.store_url_str())


@login_required
def root_redirect(request, *args, **kwargs):
    with request.user.session:
        return redirect("shopify_auth:login")


############################
# Manual API Views
############################

@login_required
@url_kwargs_match_request_user
@token_update_required
def ajax_toggle_charity(request, *args, **kwargs):
    # Submit the service for review by Ajax.
    if request.is_ajax():

        try:
            charity_instance = request.user.store_charity
        except ObjectDoesNotExist:
            charity_instance = StoreCharityHistory(store=request.user)

        # Get current context charity from kwargs
        charity = get_object_or_404(Charities, pk=kwargs['charity_id'])

        to_state = request.POST.get('to_state', None)
        if not to_state:
            return JsonResponse(data={'message': "There was an issue with the query options."},
                                        status=400)

        message = None
        if to_state == 'off':
            charity_instance.selected_charity = None
            charity_instance.save()
            message = "The charity is now disabled."
            charity_name = "None selected"
        elif to_state == 'on':
            charity_instance.selected_charity = charity
            charity_instance.save()
            message = "The charity is now enabled."
            charity_name = charity.name
        else:
            return JsonResponse(data={'message': "There was an issue with the query options."},
                                        status=400)

        try:
            create_or_assert_round_up_product(request.user)
        except Exception as e:
            logging.error(str(e.message))

        return JsonResponse(data={'message': message, 'charity_name': charity_name},
                                        status=200)

    else:
        return HttpResponseForbidden()


@login_required
@url_kwargs_match_request_user
@token_update_required
def ajax_capture_install_verification(request, *args, **kwargs):
    # Submit the service for review by Ajax.
    if request.is_ajax():

        install_verify = request.POST.get('install_verify', None)
        if not install_verify:
            return JsonResponse(data={'message': "There was an issue with the query options."},
                                        status=400)

        message = None
        if install_verify == 'true':
            request.user.userprofile.install_user_verified = True
            request.user.userprofile.save()
            message = "You have confirmed installation, if you need further help please contact support."
        else:
            return JsonResponse(data={'message': "There was an issue with the query options."},
                                        status=400)

        return JsonResponse(data={'message': message},
                                        status=200)
    else:
        return HttpResponseForbidden()


@login_required
@url_kwargs_match_request_user
@token_update_required
def ajax_help_request(request, *args, **kwargs):
    # Submit the service for review by Ajax.
    if request.is_ajax():

        # Send an email to Vesey team with query options for Collaborater account, message, and instructions
        request.user.userprofile.install_user_verified = True
        request.user.userprofile.save()

        email = request.user.userprofile.shop_contact_email

        ctx = {
                    "myshopify_domain": request.user.myshopify_domain,
                    "customer_email": email,
                    "partner_ID": settings.SHOPIFY_PARTNER_ID
        }
        subject = render_to_string("main_app/email/request_help_subject.txt", ctx)
        subject = subject.strip()
        message = render_to_string("main_app/email/request_help_body.txt", ctx)

        num_sent = EmailMessage(
            subject,
            message,
            to=[settings.HELP_TO_MAILBOX_EMAIL],
            from_email=settings.PINAX_STRIPE_INVOICE_FROM_EMAIL
        ).send()

        if num_sent and num_sent > 0:
            return JsonResponse(data={'message': "Success"},
                                        status=200)
        else:
            return JsonResponse(data={'message': "There was an when sending the message, please try again."},
                                        status=400)
    else:
        return HttpResponseForbidden()


@app_proxy
@csrf_exempt
def round_up_app_proxy(request, *args, **kwargs):
    """
    Description: This view is called via the Shopify storefront JS checkout scripts. It is called through the Shopify App Proxy functionality
    and requires an app proxy url of /tools/post-order to be setup in the app details -> extensions.
    :param request: HttpRequest object for view from storefront (verified by shopify HMAC through @app_proxy
    :param args: None
    :param kwargs: shop - the Shopify myshopify_domain in context, order_id: an order ID to create a record for.
    :return: JSON response status
    """
    if request.method == 'GET':

        try:

            shop = request.GET.get('shop', None)

            if not shop:
                return HttpResponseForbidden()

            # Get the HMAC validated origin shop as the request "user"
            user = models.AuthAppShopUser.objects.prefetch_related('userprofile', 'store_charity', 'store_charity__selected_charity').get(myshopify_domain=shop)

            if not user:
                return HttpResponseForbidden()

            if user.userprofile.round_up_product_id and user.userprofile.round_up_variant_id:

                # Get the round up text and description
                try:
                    if user.store_charity.selected_charity:
                        popover_description = user.store_charity.selected_charity.charity_product_body_html()
                    else:
                        raise ObjectDoesNotExist
                except ObjectDoesNotExist:
                    popover_description = "Donate a small portion of your purchase to support a local non-profit."

                connection.close()
                return JsonResponse(data={'variant_id': user.userprofile.round_up_variant_id,
                                    'popover_description': popover_description}, status=200)
            else:
                connection.close()
                return JsonResponse(data={'message': "Store has no round-up product."},
                                        status=400)
        except (ResourceNotFound, ObjectDoesNotExist) as e:
            logging.error("({0}-GET-SHOP-DETAILS Exception: {1}".format(str(shop), str(e.message)))
            return JsonResponse(data={'status': 'failure'}, status=404)
        except (ValueError) as e:
            logging.error("({0}-GET-SHOP-DETAILS Exception: {1}".format(str(shop), str(e.message)))
            return JsonResponse(data={'status': 'failure'}, status=403)
        except (UnauthorizedAccess) as e:
            logging.error("({0}-GET-SHOP-DETAILS Exception: {1}".format(str(shop), str(e.message)))
            return JsonResponse(data={'status': 'failure'}, status=403)
        except Exception as e:
            logging.error("({0}-GET-SHOP-DETAILS Exception: {1}".format(str(shop), str(e.message)))
            return JsonResponse(data={'status': 'failure'}, status=403)

    else:
        return HttpResponseForbidden()



############################
# App admin views (custom admin)
############################

@default_login_required(login_url='main_app:admin_login')
def admin_dashboard(request, *args, **kwargs):
    return render(request, "main_app/empty.html",)


@default_login_required(login_url='main_app:admin_login')
def admin_store_list(request, *args, **kwargs):

    template = "main_app/admin_store_list.html"
    active_menu = "stores"

    filter = StoreFilter(request.GET, queryset=AuthAppShopUser.objects.filter(adminprofile__is_admin__isnull=True).select_related('userprofile','adminprofile'))
    table = StoreTable(filter.qs, order_by='userprofile.name')
    helper = StoreFilterFormHelper()

    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    export_format = request.GET.get('_export', None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response('table.{}'.format(export_format))

    return render(request, template, {
        'table': table,
        'filter': filter,
        'helper': helper,
        'active_menu': active_menu
    })


@default_login_required(login_url='main_app:admin_login')
def admin_store_detail(request, *args, **kwargs):

    template = "main_app/admin_store_detail.html"
    active_menu = "stores"

    # Get store from kwargs
    store = get_object_or_404(AuthAppShopUser, pk=kwargs.get('pk', None))

    try:
        with shopify.Session.temp(store.myshopify_domain, store.token):
            shop_details = Shop.current()
    except (UnauthorizedAccess, ClientError):
        shop_details = None

    # Get dashboard details
    round_up_count = RoundUpOrders.objects.exclude(
        shopify_payment_status=RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED).filter(store=store).count()

    round_up_total = [
        Money(data['order_roundup_total__sum'], data['order_roundup_total_currency']) for data in
        RoundUpOrders.objects.exclude(
        shopify_payment_status=RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED).filter(store=store).values(
            'order_roundup_total_currency').annotate(Sum('order_roundup_total')).order_by()
    ]

    if round_up_total and len(round_up_total) == 1:
        round_up_total = round_up_total[0]
    else:
        round_up_total = Money(0.0, settings.DEFAULT_CURRENCY)

    stripe_customer = get_customer_for_user(store)
    stripe_invoice_count = Invoice.objects.filter(customer=stripe_customer, paid=True).count()

    stripe_invoice_sum = Invoice.objects.filter(customer=stripe_customer, paid=True).aggregate(Sum('total'))
    try:
        stripe_invoice_sum = Money(stripe_invoice_sum['total__sum'], settings.DEFAULT_CURRENCY)
    except (KeyError, InvalidOperation):
        stripe_invoice_sum = Money(0.0, settings.DEFAULT_CURRENCY)

    pending_round_up_count = RoundUpOrders.objects.exclude(
        shopify_payment_status=RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED).filter(store=store, state__in=[
        RoundUpOrders.STATE.PENDING, RoundUpOrders.STATE.PROCESSING_STRIPE_TRANSFER, RoundUpOrders.STATE.FAILED]
                                                          ).count()

    pending_round_up_total = [
        Money(data['order_roundup_total__sum'], data['order_roundup_total_currency']) for data in
        RoundUpOrders.objects.exclude(
        shopify_payment_status=RoundUpOrders.SHOPIFY_PAYMENT_STATUS.REFUNDED).filter(store=store, state__in=[
        RoundUpOrders.STATE.PENDING, RoundUpOrders.STATE.PROCESSING_STRIPE_TRANSFER, RoundUpOrders.STATE.FAILED]
                                                          ).values(
            'order_roundup_total_currency').annotate(Sum('order_roundup_total')).order_by()
    ]

    converted_currency_USD = None

    if pending_round_up_total and len(pending_round_up_total) == 1:
        pending_round_up_total = pending_round_up_total[0]

        try:
            if str(pending_round_up_total.currency) != settings.DEFAULT_CURRENCY:
                exchange = Fixer(base=str(pending_round_up_total.currency), symbols=[settings.DEFAULT_CURRENCY])
                response = exchange.convert()
                converted_currency_USD = Money(Decimal(pending_round_up_total.amount *
                                           Decimal(response['rates'][settings.DEFAULT_CURRENCY])),
                                           settings.DEFAULT_CURRENCY)
        except Exception:
            pass
    else:
        pending_round_up_total = Money(0.0, settings.DEFAULT_CURRENCY)

    subscription = Subscription.objects.filter(customer=stripe_customer).order_by('-start').first()

    if request.POST:
        subscription_lock = request.POST.get('sub-lock', None)
        switch_high = request.POST.get('switch-high', None)
        switch_low = request.POST.get('switch-low', None)

        if subscription_lock:
            if store.stripe_sub_reason.plan_locked == True:
                store.stripe_sub_reason.plan_locked = False
                store.stripe_sub_reason.save()
            elif store.stripe_sub_reason.plan_locked == False:
                store.stripe_sub_reason.plan_locked = True
                store.stripe_sub_reason.save()

        if switch_high:
            high_plan = Plan.objects.get(stripe_id=settings.PINAX_STRIPE_HIGH_VOLUME_PLAN)
            update(subscription, plan=high_plan, prorate=False)
            # Clear subscription reason
            models.StripeCustomerSubReason.objects.update_or_create(
                store=store, defaults={"subscription": subscription, 'reason': "On {0} Vesey manually moved this customer from the low usage plan to the high usage plan.".format(str(timezone.now()))}
            )
            store.stripe_sub_reason.reset_compliance()

        if switch_low:
            low_plan = Plan.objects.get(stripe_id=settings.PINAX_STRIPE_DEFAULT_PLAN)
            update(subscription, plan=low_plan, prorate=False)
            models.StripeCustomerSubReason.objects.update_or_create(
                    store=store, defaults={"subscription": subscription, 'reason': "On {0} Vesey manually moved this customer from the high usage plan to the low usage plan.".format(str(timezone.now()))}
                )
            store.stripe_sub_reason.reset_compliance()

        redirect('main_app:admin_store_detail', pk=store.id)


    return render(request, template, {
        'active_menu': active_menu,
        'store': store,
        'shopify_details': shop_details,
        'round_up_count': round_up_count,
        'round_up_total': round_up_total,
        'stripe_invoice_count': stripe_invoice_count,
        'stripe_invoice_sum': stripe_invoice_sum,
        'pending_round_up_count': pending_round_up_count,
        'pending_round_up_total': pending_round_up_total,
        'converted_currency_USD': converted_currency_USD,
        'subscription': subscription
    })


@default_login_required(login_url='main_app:admin_login')
def admin_store_roundups(request, *args, **kwargs):

    template = "main_app/admin_store_roundups.html"
    active_menu = "stores"

    # Get store from kwargs
    store = get_object_or_404(AuthAppShopUser, pk=kwargs.get('pk', None))

    table = RoundUpTable(RoundUpOrders.objects.filter(store=store).order_by('-shopify_created_at'))

    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request, template, {
        'active_menu': active_menu,
        'table': table,
        'store': store
    })


@default_login_required(login_url='main_app:admin_login')
def admin_store_transfers(request, *args, **kwargs):

    template = "main_app/admin_store_transfers.html"
    active_menu = "stores"

    # Get store from kwargs
    store = get_object_or_404(AuthAppShopUser, pk=kwargs.get('pk', None))

    stripe_customer = get_customer_for_user(store)

    table = InvoiceTable(Invoice.objects.filter(customer=stripe_customer).order_by('-period_start'))

    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request, template, {
        'active_menu': active_menu,
        'table': table,
        'store': store
    })


@default_login_required(login_url='main_app:admin_login')
def admin_charity_list(request, *args, **kwargs):

    template = "main_app/admin_charity_list.html"
    active_menu = "charity"

    filter = CharityFilter(request.GET, queryset=Charities.objects.filter())
    table = CharityTable(filter.qs, order_by='name')
    helper = CharityFilterFormHelper()

    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    export_format = request.GET.get('_export', None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response('table.{}'.format(export_format))

    return render(request, template, {
        'table': table,
        'filter': filter,
        'helper': helper,
        'active_menu': active_menu
    })


@default_login_required(login_url='main_app:admin_login')
def admin_charity_detail(request, *args, **kwargs):

    template = "main_app/admin_charity_detail.html"
    active_menu = "charity"

    # Get charity PK from kwargs
    try:
        id_charity = kwargs['pk']
    except KeyError:
        id_charity = None

    if id_charity is None:
        charity = Charities()
    else:
        charity = get_object_or_404(Charities, pk=id_charity)

    if request.method == "POST":

        if 'delete' in request.POST:
            charity.delete()

            messages.success(request, "Charity was deleted.")
            return redirect('main_app:admin_charity_list')

        form = forms.AdminCharityForm(request.POST, request.FILES, instance=charity)

        if not form.is_valid():
            return render(request, template, {"form":form, 'active_menu': active_menu})

        if form.is_valid():
            form.save()
            messages.success(request, "Charity was saved successfully.")

            return redirect('main_app:admin_charity_list')

    else:
        form = forms.AdminCharityForm(instance=charity)

        return render(request, template, {"form":form, 'active_menu': active_menu})


@default_login_required(login_url='main_app:admin_login')
def admin_transfer_list(request, *args, **kwargs):

    template = "main_app/admin_transfer_list.html"
    active_menu = "transfer"

    filter = InvoiceFilter(request.GET, queryset=Invoice.objects.filter())
    table = AllInvoiceTable(filter.qs)
    helper = TransferFilterFormHelper()

    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    export_format = request.GET.get('_export', None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response('table.{}'.format(export_format))

    return render(request, template, {
        'table': table,
        'filter': filter,
        'helper': helper,
        'active_menu': active_menu
    })


@default_login_required(login_url='main_app:admin_login')
def dev_actions(request, *args, **kwargs):

    template = "main_app/admin_blank.html"
    active_menu = "transfer"

    manual_order_sync()

    return render(request, template, {
        'active_menu': active_menu
    })