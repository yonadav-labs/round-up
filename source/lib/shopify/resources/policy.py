from source.lib.shopify.base import ShopifyResource
from shopify import mixins


class Policy(ShopifyResource, mixins.Metafields, mixins.Events):
  pass
