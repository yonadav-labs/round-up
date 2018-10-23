from source.lib.shopify.base import ShopifyResource
from source.lib.shopify.resources.customer import Customer


class CustomerSavedSearch(ShopifyResource):

    def customers(cls, **kwargs):
        return Customer._build_list(cls.get("customers", **kwargs))
