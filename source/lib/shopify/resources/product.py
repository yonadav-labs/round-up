from source.lib.shopify.base import ShopifyResource
from .. import mixins


class Product(ShopifyResource, mixins.Metafields, mixins.Events):

    def price_range(self):
        prices = [float(variant.price) for variant in self.variants]
        f = "%0.2f"
        min_price = min(prices)
        max_price = max(prices)
        if min_price != max_price:
            return "%s - %s" % (f % min_price, f % max_price)
        else:
            return f % min_price

    def add_variant(self, variant):
        variant.attributes['product_id'] = self.id
        return variant.save()
