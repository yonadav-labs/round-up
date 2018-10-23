import base64
import cStringIO
import logging
import urllib

from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from PIL import Image as PILImage

from source.lib import shopify
from source.lib.pyactiveresource.connection import ResourceNotFound, ForbiddenAccess
from source.lib.shopify.resources.asset import Asset
from source.lib.shopify.resources.image import Image
from source.lib.shopify.resources.product import Product
from source.lib.shopify.resources.script_tag import ScriptTag
from source.lib.shopify.resources.shop import Shop
from source.lib.shopify.resources.theme import Theme
from source.lib.shopify.resources.variant import Variant
from moneyed.localization import _FORMATTER


__author__ = 'JLCJ'
from django.conf import settings

def remove_whitespace(string):
        return ''.join(string.split())


def image_src_by_id(product_images, image_id):
    if not image_id:
        return None

    image_src = None
    for image in product_images:
        if image.id == image_id:
            image_src = image.src
            break
    return image_src


def create_new_shopify_product(store, selected_charity=None):
    round_up_product = Product()

    if selected_charity:
        round_up_product.title = selected_charity.charity_product_str()
    else:
        round_up_product.title = "Round Up"

    if selected_charity:
        round_up_product.body_html = selected_charity.charity_product_body_html()
    else:
        round_up_product.body_html = "Round Up"

    round_up_product.vendor = ""
    round_up_product.product_type = "round_up"

    image = Image()

    if selected_charity:
        if selected_charity.charity_logo:
            image.src = selected_charity.charity_logo.url
        else:
            image.src = settings.DEFAULT_IMAGE_LOCATION
    else:
        image.src = settings.DEFAULT_IMAGE_LOCATION

    round_up_product.images = [image]

    variant = Variant()
    variant.price = "0.01"
    variant.requires_shipping = False
    variant.taxable = False
    round_up_product.variants = [variant]

    round_up_product.save()

    return round_up_product.id, round_up_product.variants[0].id


def get_base_64_string(image_url):
    try:
        file = cStringIO.StringIO(urllib.urlopen(image_url).read())
        img = PILImage.open(file)
        buffer = cStringIO.StringIO()
        img.save(buffer, format=img.format)
        img_str = base64.b64encode(buffer.getvalue())
        return img_str
    except:
        return None


def update_existing_shopify_product(store, shopify_product, selected_charity=None):
    change_required = False

    # Compare product title
    if selected_charity:
        if shopify_product.title != selected_charity.charity_product_str():
            shopify_product.title = selected_charity.charity_product_str()
            change_required = True
    elif not selected_charity:
        if shopify_product.title != "Round Up":
            shopify_product.title = "Round Up"
            change_required = True

    # Compare product body
    if selected_charity:
        if shopify_product.body_html != selected_charity.charity_product_body_html():
            shopify_product.body_html = selected_charity.charity_product_body_html()
            change_required = True
    elif not selected_charity:
        if shopify_product.body_html != "Round Up":
            shopify_product.body_html = "Round Up"
            change_required = True

    # Compare product body
    deleted_images = False
    for image in shopify_product.images:

        # Get Shopify image as base64 string
        shopify_image_base64 = get_base_64_string(image.src)

        # Get default charity image as base64 string
        try:
            if selected_charity:
                default_image_base64 = get_base_64_string(selected_charity.charity_logo.url)
            else:
                default_image_base64 = get_base_64_string(settings.DEFAULT_IMAGE_LOCATION)
        except (ValueError, ObjectDoesNotExist):
            default_image_base64 = get_base_64_string(settings.DEFAULT_IMAGE_LOCATION)

        if shopify_image_base64 != default_image_base64:
            try:
                image.destroy()
            except ResourceNotFound:
                pass
            deleted_images = True

    # If there isn't a product image or if the images were cleared because they did not match
    if not shopify_product.images or deleted_images:

        image = Image()

        if selected_charity:
            try:
                if selected_charity.charity_logo:
                    image.src = selected_charity.charity_logo.url
                else:
                    image.src = settings.DEFAULT_IMAGE_LOCATION
            except (ValueError, ObjectDoesNotExist):
                image.src = settings.DEFAULT_IMAGE_LOCATION
        else:
            image.src = settings.DEFAULT_IMAGE_LOCATION

        shopify_product.images = [image]

        change_required = True

    if change_required:
        shopify_product.save()
        return True

    return False


def create_or_assert_round_up_product(store, deleted=False):
    with shopify.Session.temp(store.myshopify_domain, store.token):
        # Check if store has round up product and that it exists in Shopify.
        round_up_product_id = store.userprofile.round_up_product_id
        shopify_product = None
        difference = False

        try:
            selected_charity = store.store_charity.selected_charity
        except ObjectDoesNotExist:
            selected_charity = None

        if round_up_product_id:
            if deleted:
                shopify_product = None
            else:
                try:
                    shopify_product = Product.find(store.userprofile.round_up_product_id)
                except ResourceNotFound:
                    # Create a round up product
                    shopify_product = None

        # Does the user have a charity selected?
        if selected_charity:
            # If no existing product (or product has been marked as deleted) create one for the charity
            if not shopify_product:
                product_id, variant_id = create_new_shopify_product(store, selected_charity)
                store.userprofile.round_up_product_id = product_id
                store.userprofile.round_up_variant_id = variant_id
                store.userprofile.save()

            # If existing product compare against charity, update if required
            elif shopify_product:
                updated = update_existing_shopify_product(store, shopify_product, selected_charity)

        elif not selected_charity:
            # If no existing product (or product has been marked as deleted) create one for the charity
            if not shopify_product:
                product_id, variant_id = create_new_shopify_product(store)
                store.userprofile.round_up_product_id = product_id
                store.userprofile.round_up_variant_id = variant_id
                store.userprofile.save()

            # If existing product compare against charrity, update if required
            elif shopify_product:
                updated = update_existing_shopify_product(store, shopify_product)


def create_or_update_tag(key):
    # Create a script tag to load he dynamic HTML content into Shopify checkout.
    created = False

    if key:
        try:
            script = ScriptTag.find(key)
        except ResourceNotFound as e:
            script = ScriptTag()
            created = True
    else:
        script = ScriptTag()
        created = True

    return script, created


def create_or_assert_tag(store, asset):

    script, script_created = create_or_update_tag(store.userprofile.round_up_js_script_id)

    url = asset.public_url
    if '.liquid' in url:
        url = url.replace('.liquid', '')

    try:
        script.src = url
        script.event="onload"
        script.display_scope = "online_store"
        script.save()
    except ForbiddenAccess:
        pass

    if script_created:
        store.userprofile.round_up_js_script_id = script.id
        store.userprofile.save()


def create_or_assert_round_up_asset(store):
    with shopify.Session.temp(store.myshopify_domain, store.token):
        # Get current theme
        current_theme = Theme.find(role="main")
        current_theme = current_theme[0]

        # Get the current FQDN
        current_shopify_shop = Shop.current()
        current_domain = current_shopify_shop.domain
        current_currency_code = current_shopify_shop.currency

        if not current_theme:
            raise NotImplementedError("A current theme does not exist for the store.")

        context = {
                   'shopify_domain': store.myshopify_domain,
                   'current_domain': current_domain
        }

        # Add CSS assets to theme assets folder.
        css_content = render_to_string('main_app/liquid/round_up.css', context=context)
        key = "assets/round_up.css"

        try:
            asset = Asset.find(theme_id=current_theme.id, key=key)
            if asset.value != css_content:
                asset.value = css_content
                asset.save()
        except (ResourceNotFound) as e:
            asset = Asset(dict(key=key, theme_id=current_theme.id))
            asset.value = css_content
            asset.save()

        try:
            if store.store_charity.selected_charity:
                popover_description = store.store_charity.selected_charity.charity_product_body_html()
            else:
                raise ObjectDoesNotExist
        except ObjectDoesNotExist:
            popover_description = "Donate a small portion of your purchase to support a local non-profit."


        # Get currency code:
        try:
            if current_currency_code == 'USD':
                money_symbol = _FORMATTER.get_sign_definition(current_currency_code, "en_US")[0]
            else:
                money_symbol = _FORMATTER.get_sign_definition(current_currency_code, "DEFAULT")[0]
        except:
            money_symbol = '$'

        context = {
                   'shopify_domain': store.myshopify_domain,
                   'current_domain': current_domain,
                   'product_variant_id': store.userprofile.round_up_variant_id,
                   'round_up_popover_description': popover_description,
                   'money_symbol': money_symbol
        }

        # Add JS assets to theme assets folder.
        liquid_content = render_to_string('main_app/liquid/round_up.js.liquid', context=context)
        key = "assets/round_up.js.liquid"

        try:
            js_asset = Asset.find(theme_id=current_theme.id, key=key)
            if js_asset.value != liquid_content:
                js_asset.value = liquid_content
                js_asset.save()
        except (ResourceNotFound) as e:
            js_asset = Asset(dict(key=key, theme_id=current_theme.id))
            js_asset.value = liquid_content
            js_asset.save()

        # Remove orphaned script tags
        all_app_scripts = ScriptTag.find()
        try:
            for script in all_app_scripts:
                if not script.id in [store.userprofile.round_up_js_script_id]:
                    script.destroy()
        except ForbiddenAccess:
            pass

        # Add the JS asset as a script tag to online store pages
        create_or_assert_tag(store, js_asset)

        return