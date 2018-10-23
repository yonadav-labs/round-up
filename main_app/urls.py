# Like Keys URL
from django.conf.urls import url
from django.contrib.auth.views import login, logout

from . import views
from main_app.forms import AdminAuthenticationForm


urlpatterns = [
    url(r'^admin/sign-in/$', login, {
        'authentication_form': AdminAuthenticationForm},
        name='admin_login'),

    url(r'^admin/logout/$',
    logout, name='admin_logout'),

    url(r'^$', views.root_redirect, name="root_redirect"),
    url(r'^redirect/$', views.login_redirect, name="login_redirect"),

    # Admin routes

    url(r'^admin/dashboard/$', views.admin_dashboard, name='admin_dashboard'),
    url(r'^admin/stores/$', views.admin_store_list, name='admin_store_list'),
    url(r'^admin/stores/(?P<pk>[0-9]+)/$', views.admin_store_detail, name='admin_store_detail'),
    url(r'^admin/stores/(?P<pk>[0-9]+)/roundups/$', views.admin_store_roundups, name='admin_store_roundups'),
    url(r'^admin/stores/(?P<pk>[0-9]+)/transfers/$', views.admin_store_transfers, name='admin_store_transfers'),
    url(r'^admin/charity/$', views.admin_charity_list, name='admin_charity_list'),
    url(r'^admin/charity/detail/$', views.admin_charity_detail, name='admin_charity_edit'),
    url(r'^admin/charity/detail/(?P<pk>[0-9]+)/$', views.admin_charity_detail, name='admin_charity_detail'),
    url(r'^admin/transfers/$', views.admin_transfer_list, name='admin_transfer_list'),
    url(r'^admin/dev-action/$', views.dev_actions, name='dev_actions'),

    # App routes
    url(r'^(?P<store_url>[-\w]+)/$', views.order_list, name='home_page'),
    url(r'^(?P<store_url>[-\w]+)/onboarding/$', views.onboarding_wizard, name='onboarding_wizard'),
    url(r'^(?P<store_url>[-\w]+)/onboarding/confirm_install/$', views.ajax_capture_install_verification, name='ajax_capture_install_verification'),
    url(r'^(?P<store_url>[-\w]+)/request-help/$', views.ajax_help_request, name='ajax_help_request'),
    url(r'^(?P<store_url>[-\w]+)/tutorial/$', views.tutorial, name='tutorial'),
    url(r'^(?P<store_url>[-\w]+)/about/$', views.about, name='about'),
    url(r'^(?P<store_url>[-\w]+)/charity/$', views.charity_selection, name='charity_selection'),
    url(r'^(?P<store_url>[-\w]+)/charity/(?P<charity_id>[0-9]+)/toggle/$', views.ajax_toggle_charity, name="ajax_toggle_charity"),
    url(r'^(?P<store_url>[-\w]+)/contact/$', views.contact, name='contact'),
    url(r'^(?P<store_url>[-\w]+)/payment/$', views.payment_information, name='payment_information'),
    url(r'^(?P<store_url>[-\w]+)/round_up_orders/$', views.order_list, name='transaction_list'),
    url(r'^(?P<store_url>[-\w]+)/payment/history/$', views.invoice_list, name='invoice_list'),

    url(r'^api/round-up/$', views.round_up_app_proxy, name='proxy_view'),


]
