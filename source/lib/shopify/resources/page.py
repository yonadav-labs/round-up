from source.lib.shopify.base import ShopifyResource
from shopify import mixins


class Page(ShopifyResource, mixins.Metafields, mixins.Events):
    pass
