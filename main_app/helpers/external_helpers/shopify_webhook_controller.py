from source.lib import shopify
from source.lib.shopify.resources.webhook import Webhook


def get_return_fields(topic):
    try:
        if topic.split("/")[0] == 'products':
            return ["id","title","variants","updated_at","images"]
        elif topic.split("/")[0] == 'shop':
            return ["id","updated_at","timezone","iana_timezone","currency", "name", "email", "plan_display_name", "plan_name", "myshopify_domain"]
        else:
            return []
    except:
        return []


def create_or_update_webhooks(user, full_url):
    """
    Purpose: This function will create, or ensure that they are created all required application
    webhooks (shop update, product update/delete, and app uninstall.
    :param full_url: get the POST url for webhook created from the shopify_webhook module
    :param user: the authenticated and verified user to create a webhook for
    :param webhook_topic: what webhook to register
    :return: true on success, false on fail
    """
    if user.token and user.token != '00000000000000000000000000000000':
        with shopify.Session.temp(user.myshopify_domain, user.token):
            required_webhook_topics = ["app/uninstalled",
                                       "shop/update",
                                       "products/delete",
                                       "products/update"
                                       ]

            # Check to see if the required webhooks exist for the current Shopify shop.
            shop_webhooks = Webhook.find()

            for required_webhook in required_webhook_topics:
                webhook_found_and_accurate = False

                for shopify_webhook in shop_webhooks:

                    expected_fields = get_return_fields(shopify_webhook.topic)

                    # Do the required webhooks exist?
                    if required_webhook == shopify_webhook.topic:
                        if shopify_webhook.format == "json" and shopify_webhook.address == full_url and \
                                        shopify_webhook.fields == expected_fields:
                                webhook_found_and_accurate = True
                                break
                        else:
                            shopify_webhook.address = full_url
                            shopify_webhook.format = "json"
                            if expected_fields:
                                shopify_webhook.fields = expected_fields
                            shopify_webhook.save()
                            webhook_found_and_accurate = True
                            break

                if not webhook_found_and_accurate:
                # If a webhook does not exist, create it.
                    new_webhook = Webhook()
                    new_webhook.topic = required_webhook
                    new_webhook.address = full_url
                    new_webhook.format = "json"
                    expected_fields = get_return_fields(required_webhook)
                    if expected_fields:
                        new_webhook.fields = expected_fields
                    new_webhook.save()
