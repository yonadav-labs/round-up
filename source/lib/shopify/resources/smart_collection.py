from .product import Product
from source.lib.shopify import mixins
from source.lib.shopify.base import ShopifyResource




class SmartCollection(ShopifyResource, mixins.Metafields, mixins.Events):

    def products(self):
        return Product.find(collection_id=self.id)
