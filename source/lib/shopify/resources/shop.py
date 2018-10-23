from ...shopify.base import ShopifyResource
from source.lib.shopify.resources.metafield import Metafield
from source.lib.shopify.resources.event import Event


class Shop(ShopifyResource):

    @classmethod
    def current(cls):
        return cls.find_one("/admin/shop." + cls.format.extension)

    def metafields(self):
        return Metafield.find()

    def add_metafield(self, metafield):
        if self.is_new():
            raise ValueError("You can only add metafields to a resource that has been saved")
        metafield.save()
        return metafield

    def events(self):
        return Event.find()
