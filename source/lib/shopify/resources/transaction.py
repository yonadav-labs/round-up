from source.lib.shopify.base import ShopifyResource


class Transaction(ShopifyResource):
    _prefix_source = "/admin/orders/$order_id/"
