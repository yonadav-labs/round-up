from django.urls import reverse
from django.utils.safestring import mark_safe
import django_tables2 as tables
from djmoney.money import Money
from easy_thumbnails.files import get_thumbnailer
from pinax.stripe.models import Invoice

from main_app.models import AuthAppShopUser, RoundUpOrders, Charities


class StoreTable(tables.Table):
    edit = tables.LinkColumn('item_edit', args=[AuthAppShopUser('pk')], orderable=False, empty_values=(),
                             exclude_from_export=True)
    class Meta:
        model = AuthAppShopUser
        template = 'django_tables2/bootstrap.html'
        fields = ['userprofile.name', 'myshopify_domain', 'userprofile.created', 'edit']

    def render_edit(self, record):
        return mark_safe('<a href='+reverse("main_app:admin_store_detail", kwargs={'pk':record.pk})+' class="btn btn-info btn-xs">View <div class="fa fa-angle-right"></div></a>')


class CustomerRoundUpTable(tables.Table):
    class Meta:
        empty_text = "There are currently no round up orders for your store."
        model = RoundUpOrders
        template = 'django_tables2/bootstrap.html'
        fields = ['shopify_created_at', 'order_name', 'order_total', 'order_roundup_total', 'shopify_payment_status', 'state']

    def render_state(self, record):
        if record.state == RoundUpOrders.STATE.PENDING:
            return mark_safe('<span class="label label-default">Pending Stripe Transfer</span>')
        elif record.state == RoundUpOrders.STATE.TRANSFERRED:
            return mark_safe('<span class="label label-success">Transferred to Stripe</span>')
        elif record.state == RoundUpOrders.STATE.PROCESSING_STRIPE_TRANSFER:
            return mark_safe('<span class="label label-info">Stripe Transfer in Progress</span>')
        else:
            return mark_safe('<span class="label label-danger">' + record.get_state_display() + '</span>')

    def render_shopify_payment_status(self, record):
        if record.shopify_payment_status == RoundUpOrders.SHOPIFY_PAYMENT_STATUS.PAID:
            return mark_safe('<span class="label label-default">Charity paid</span>')
        else:
            return mark_safe('<span class="label label-danger">' + record.get_shopify_payment_status_display() + '</span>')


class RoundUpTable(tables.Table):
    class Meta:
        empty_text = "There are currently no round up orders for this store."
        model = RoundUpOrders
        template = 'django_tables2/bootstrap.html'
        fields = ['shopify_created_at', 'order_name', 'order_total', 'order_roundup_total', 'shopify_payment_status', 'state', 'stripe_invoice']

    def render_state(self, record):
        if record.state == RoundUpOrders.STATE.PENDING:
            return mark_safe('<span class="label label-default">Pending Stripe Transfer</span>')
        elif record.state == RoundUpOrders.STATE.TRANSFERRED:
            return mark_safe('<span class="label label-success">Transferred to Stripe</span>')
        elif record.state == RoundUpOrders.STATE.PROCESSING_STRIPE_TRANSFER:
            return mark_safe('<span class="label label-info">Stripe Transfer in Progress</span>')
        else:
            return mark_safe('<span class="label label-danger">' + record.get_state_display() + '</span>')

    def render_shopify_payment_status(self, record):
        if record.shopify_payment_status == RoundUpOrders.SHOPIFY_PAYMENT_STATUS.PAID:
            return mark_safe('<span class="label label-default">Charity paid</span>')
        else:
            return mark_safe('<span class="label label-danger">' + record.get_shopify_payment_status_display() + '</span>')

    def render_stripe_invoice(self, record):
        if record.stripe_invoice:
            return mark_safe('<a href="https://dashboard.stripe.com/invoices/' + str(record.stripe_invoice.stripe_id) + '">View on Stripe</a>')
        else:
            return


class InvoiceTable(tables.Table):
    class Meta:
        empty_text = "There are currently no invoices for this store."
        model = Invoice
        template = 'django_tables2/bootstrap.html'
        fields = ['stripe_id', 'period_start', 'period_end', 'amount_due', 'total', 'attempt_count', 'status',]

    def render_stripe_id(self, record):
        if record.stripe_id:
            return mark_safe('<a href="https://dashboard.stripe.com/invoices/' + str(record.stripe_id) + '">' + str(record.stripe_id) + '</a>')
        else:
            return None

    def render_status(self, record):
        if record.status == "Open":
            return mark_safe('<span class="label label-default">Open</span>')
        elif record.status == "Paid":
            return mark_safe('<span class="label label-success">Paid</span>')
        else:
            return mark_safe('<span class="label label-danger">' + str(record.status) + '</span>')

    def render_amount_due(self, record):
        return Money(record.amount_due, record.currency)

    def render_total(self, record):
        return Money(record.total, record.currency)


class CustomerInvoiceTable(tables.Table):
    class Meta:
        empty_text = "There are currently no invoices for your store's donations."
        model = Invoice
        template = 'django_tables2/bootstrap.html'
        fields = ['stripe_id', 'date', 'period_start', 'period_end', 'amount_due', 'total', 'attempt_count', 'status',]

    def render_status(self, record):
        if record.status == "Open":
            return mark_safe('<span class="label label-default">Open</span>')
        elif record.status == "Paid":
            return mark_safe('<span class="label label-success">Paid</span>')
        else:
            return mark_safe('<span class="label label-danger">' + str(record.status) + '</span>')

    def render_amount_due(self, record):
        return Money(record.amount_due, record.currency)

    def render_total(self, record):
        return Money(record.total, record.currency)


class ImageColumn(tables.Column):
     def render(self, value):
         if value:
            thumb_url = get_thumbnailer(value)['charity_logo'].url
            return mark_safe('<img class="img-thumbnail" src="{0}" alt="{1} thumbnail" />'.format(thumb_url, value.name))
         else:
             return '-'


class CharityTable(tables.Table):
    charity_logo = ImageColumn()
    edit = tables.LinkColumn('item_edit', args=[Charities('pk')], orderable=False, empty_values=(),
                             exclude_from_export=True)
    class Meta:
        model = Charities
        template = 'django_tables2/bootstrap.html'
        fields = ['charity_logo', 'name', 'description', 'website', 'created', 'edit']

    def render_edit(self, record):
        return mark_safe('<a href='+reverse("main_app:admin_charity_detail", kwargs={'pk':record.pk})+' class="btn btn-info btn-xs">View <div class="fa fa-angle-right"></div></a>')


class AllInvoiceTable(tables.Table):
    class Meta:
        empty_text = "There are currently no invoices."
        model = Invoice
        template = 'django_tables2/bootstrap.html'
        fields = ['customer', 'stripe_id', 'period_start', 'period_end', 'amount_due', 'total', 'attempt_count', 'status']

    def render_amount_due(self, record):
        return Money(record.amount_due, record.currency)

    def render_total(self, record):
        return Money(record.total, record.currency)

    def render_stripe_id(self, record):
        if record.stripe_id:
            return mark_safe('<a href="https://dashboard.stripe.com/invoices/' + str(record.stripe_id) + '">' + str(record.stripe_id) + '</a>')
        else:
            return None

    def render_status(self, record):
        if record.status == "Open":
            return mark_safe('<span class="label label-default">Open</span>')
        elif record.status == "Paid":
            return mark_safe('<span class="label label-success">Paid</span>')
        else:
            return mark_safe('<span class="label label-danger">' + str(record.status) + '</span>')