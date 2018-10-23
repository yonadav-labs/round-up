import django_filters
from pinax.stripe.models import Invoice

from main_app.models import AuthAppShopUser


class StoreFilter(django_filters.FilterSet):
    myshopify_domain = django_filters.CharFilter(lookup_expr='icontains')
    userprofile__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = AuthAppShopUser
        fields = ['myshopify_domain', 'userprofile__name']


class CharityFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    website = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = AuthAppShopUser
        fields = ['name', 'website']


class InvoiceFilter(django_filters.FilterSet):
    customer__user__myshopify_domain = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Invoice
        fields = ['customer__user__myshopify_domain']