from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import python_2_unicode_compatible
from djmoney.models.fields import MoneyField
from easy_thumbnails.fields import ThumbnailerImageField
from pinax.stripe.models import Subscription, Invoice
from django.db import models
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.auth.signals import user_logged_in

from source.lib.shopify_auth.models import AbstractShopUser


class AuthAppShopUser(AbstractShopUser):
    pass

    def clear_user_sessions(self):
        user_sessions = UserSession.objects.filter(user = self)
        for user_session in user_sessions:
            user_session.session.delete()

    def store_url_str(self):
        store_url = str(self)

        idx = store_url.find(".")
        if idx != -1:
            store_url = store_url[0:idx]
        if len(store_url) == 0:
            return None
        return store_url

    def has_charity(self):
        try:
            if self.store_charity.selected_charity:
                return True
            else:
                return False
        except ObjectDoesNotExist:
            return False

    def has_verified_install(self):
        try:
            if self.userprofile.install_user_verified:
                return True
            else:
                return False
        except ObjectDoesNotExist:
            return False

    def active_installation(self):
        if self.token and self.token != '00000000000000000000000000000000':
            return True
        else:
            return False


class UserProfile(models.Model):
    user = models.OneToOneField(AuthAppShopUser, on_delete=models.CASCADE)

    name = models.CharField(max_length=256, blank=True, null=True)

    display_timezone = models.CharField(max_length=128)
    iana_timezone = models.CharField(max_length=128)
    latest_order_sync_time = models.DateTimeField(blank=True, null=True)
    latest_stripe_billing_period_end_time = models.DateTimeField(blank=True, null=True)

    shop_contact_email = models.EmailField(blank=True, null=True)

    setup_required = models.BooleanField(default=True)
    install_user_verified = models.BooleanField(default=False)

    round_up_product_id = models.BigIntegerField(blank=True, null=True)
    round_up_variant_id = models.BigIntegerField(blank=True, null=True)
    round_up_js_script_id = models.BigIntegerField(blank=True, null=True)

    welcome_email_sent = models.BooleanField(default=False)
    onboarding_email_sent = models.BooleanField(default=False)
    review_email_sent = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.created = timezone.now()

        self.modified = timezone.now()
        return super(UserProfile, self).save(*args, **kwargs)


class AdminProfile(models.Model):
    user = models.OneToOneField(AuthAppShopUser, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)


class UserSession(models.Model):
    user = models.ForeignKey(AuthAppShopUser)
    session = models.ForeignKey(Session)


class TermsAndConditionText(models.Model):
    current_terms = models.TextField(default='Terms text content')


def user_logged_in_handler(sender, request, user, **kwargs):
    UserSession.objects.get_or_create(
        user = user,
        session_id = request.session.session_key
    )
user_logged_in.connect(user_logged_in_handler)


@python_2_unicode_compatible
class Charities(models.Model):
    name = models.CharField(max_length=128)

    charity_logo = ThumbnailerImageField(upload_to='charity_logos/', blank=True)
    website = models.URLField()
    description = models.TextField()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name.encode('utf8')

    def charity_product_str(self):
        return "Round Up for " + self.name.encode('utf8')

    def charity_product_body_html(self):
        return "Donate a small portion of your purchase to support the <a href='{0}' target='_blank'>{1}</a>.".format(str(self.website), self.name.encode('utf8'))

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.created = timezone.now()

        self.modified = timezone.now()
        return super(Charities, self).save(*args, **kwargs)


class StoreCharityHistory(models.Model):
    store = models.OneToOneField(AuthAppShopUser, on_delete=models.CASCADE, related_name="store_charity")
    selected_charity = models.ForeignKey(Charities, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.selected_charity + ' - ' + str(self.store)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.created = timezone.now()

        self.modified = timezone.now()
        return super(StoreCharityHistory, self).save(*args, **kwargs)


class RoundUpOrders(models.Model):
    class STATE:
        PENDING = 'PG'
        PROCESSING_STRIPE_TRANSFER = 'PS'
        FAILED = 'PF'
        TRANSFERRED = 'TF'

    class SHOPIFY_PAYMENT_STATUS:
        PAID = 'PD'
        PARTIALLY_PAID = 'PP'
        PARTIALLY_REFUNDED = 'PR'
        REFUNDED = 'RD'

    store = models.ForeignKey(AuthAppShopUser, related_name='store_roundups')

    order_number = models.BigIntegerField(unique=True)
    order_name = models.CharField(max_length=256)
    order_total = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')
    order_roundup_total = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')
    shopify_created_at = models.DateTimeField()
    stripe_invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='invoice_orders')

    STATE_CHOICES = (
        (STATE.PENDING, "Pending Stripe Transfer"),
        (STATE.PROCESSING_STRIPE_TRANSFER, "Stripe Transfer in Progress"),
        (STATE.TRANSFERRED, "Transferred to Stripe"),
        (STATE.FAILED, "Stripe payment failed"),
    )
    state = models.CharField(max_length=2, default=STATE.PENDING, choices=STATE_CHOICES, blank=True, null=True)

    SHOPIFY_PAYMENT_CHOICES = (
        (SHOPIFY_PAYMENT_STATUS.PAID, "Charity paid"),
        (SHOPIFY_PAYMENT_STATUS.PARTIALLY_PAID, "Charity partially paid"),
        (SHOPIFY_PAYMENT_STATUS.PARTIALLY_REFUNDED, "Charity partially refunded"),
        (SHOPIFY_PAYMENT_STATUS.REFUNDED, "Charity refunded"),
    )
    shopify_payment_status = models.CharField(max_length=2, default=SHOPIFY_PAYMENT_STATUS.PAID, choices=SHOPIFY_PAYMENT_CHOICES,
                             blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('store', 'order_number',)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.created = timezone.now()

        self.modified = timezone.now()
        return super(RoundUpOrders, self).save(*args, **kwargs)

    def pretty_print(self):
        return "Order # / Name: {0} / {1}\n  Order total: {2}\n  Order Round Up Total: {3}".format(str(self.order_number),
                                                                                                   str(self.order_name),
                                                                                                   str(self.order_total),
                                                                                                   str(self.order_roundup_total))


class StripeCustomerSubReason(models.Model):
    store =  models.OneToOneField(AuthAppShopUser, on_delete=models.CASCADE, related_name="stripe_sub_reason")

    subscription = models.OneToOneField(Subscription, blank=True, null=True, on_delete=models.SET_NULL,
                                        related_name="stripe_sub")

    reason = models.CharField(max_length=512, null=True, blank=True)
    low_plan_compliance_tracker = models.IntegerField(default=0)
    high_plan_compliance_tracker = models.IntegerField(default=0)
    plan_locked = models.BooleanField(default=False)

    def fail_low_compliance(self):
        self.low_plan_compliance_tracker += 1
        self.high_plan_compliance_tracker = 0
        self.save()

    def pass_low_compliance(self):
        self.low_plan_compliance_tracker = 0
        self.high_plan_compliance_tracker = 0
        self.save()

    def reset_compliance(self):
        self.low_plan_compliance_tracker = 0
        self.high_plan_compliance_tracker = 0
        self.save()

    def fail_high_compliance(self):
        self.low_plan_compliance_tracker = 0
        self.high_plan_compliance_tracker += 1
        self.save()

    def pass_high_compliance(self):
        self.low_plan_compliance_tracker = 0
        self.high_plan_compliance_tracker = 0
        self.save()

    def in_compliance(self):
        if self.low_plan_compliance_tracker >= 3:
            return False

        if self.high_plan_compliance_tracker >= 3:
            return False

        return True


class InvoiceCharityLink(models.Model):
    store = models.OneToOneField(AuthAppShopUser, on_delete=models.CASCADE, related_name="invoice_charity_history")
    mapped_charity = models.ForeignKey(Charities, null=True, blank=True)
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='invoice_charity')

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.selected_charity + ' - ' + str(self.store)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.created = timezone.now()

        self.modified = timezone.now()
        return super(InvoiceCharityLink, self).save(*args, **kwargs)