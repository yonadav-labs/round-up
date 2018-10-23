from source.lib.shopify.base import ShopifyResource


class FulfillmentService(ShopifyResource):
    def __get_format(self):
        return self.attributes.get("format")

    def __set_format(self, data):
        self.attributes["format"] = data

    format = property(__get_format, __set_format, None, "Format attribute")
