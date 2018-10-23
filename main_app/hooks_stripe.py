from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from pinax.stripe.hooks import DefaultHookSet
from django.contrib.sites.models import Site


class HookSet(DefaultHookSet):

    def adjust_subscription_quantity(self, customer, plan, quantity):
        """
        Given a customer, plan, and quantity, when calling Customer.subscribe
        you have the opportunity to override the quantity that was specified.

        Previously this was handled in the setting `PAYMENTS_PLAN_QUANTITY_CALLBACK`
        and was only passed a customer object.
        """
        if quantity is None:
            quantity = 1
        return quantity

    def trial_period(self, user, plan):
        """
        Given a user and plan, return an end date for a trial period, or None
        for no trial period.

        Was previously in the setting `TRIAL_PERIOD_FOR_USER_CALLBACK`
        """
        return None

    def send_receipt(self, charge, email=None):
        from pinax.stripe.models import Charge

        if not charge.receipt_sent:

            try:
                db_charge = Charge.objects.get(stripe_id=charge.stripe_id)
            except ObjectDoesNotExist:
                db_charge = None

            if db_charge and db_charge.receipt_sent:
                charge.save()
                return

            if charge.paid:
                charge.receipt_sent = 1
                charge.save()
                return

            site = Site.objects.get_current()
            protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")

            current_charity_name = "No charity selected - Vesey Directed Donation"

            if charge.customer:
                try:
                    if charge.customer.user.store_charity.selected_charity.name:
                        current_charity_name = charge.customer.user.store_charity.selected_charity.name
                except ObjectDoesNotExist:
                    current_charity_name = "No charity selected - Vesey Directed Donation"

            ctx = {
                "charge": charge,
                "site": site,
                "protocol": protocol,
                'current_charity_name': current_charity_name
            }
            subject = render_to_string("pinax/stripe/email/subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("pinax/stripe/email/body.txt", ctx)

            if not email and charge.customer:
                email = charge.customer.user.userprofile.shop_contact_email

            num_sent = EmailMessage(
                subject,
                message,
                to=[email],
                from_email=settings.PINAX_STRIPE_INVOICE_FROM_EMAIL
            ).send()
            charge.receipt_sent = num_sent and num_sent > 0
            charge.save()