#!/usr/bin/python
# -*- coding: utf-8 -*-

class DefaultLayout(object):
    def __init__(self):
        self.layout_fields = []
        
    def configure_layout_fields(self, layout_style):
        if layout_style == 1:
            self.layout_fields = [
            {
                "id" : None,
                "custom_field_name" : "Transaction Id",
                "export_field_order" : 0,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 16
            },
            {
                "id" : None,
                "custom_field_name" : "Buyer note",
                "export_field_order" : 1,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            },
            {
                "id" : None,
                "custom_field_name" : "Buyer id",
                "export_field_order" : 2,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            },
            {
                "id" : None,
                "custom_field_name" : "Email address",
                "export_field_order" : 3,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            },
            {
                "id" : None,
                "custom_field_name" : "Ship Name",
                "export_field_order" : 4,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 21
            },
            {
                "id" : None,
                "custom_field_name" : "Ship Address 1",
                "export_field_order" : 5,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 24
            },
            {
                "id" : None,
                "custom_field_name" : "Ship Address 2",
                "export_field_order" : 6,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 25
            },
            {
                "id" : None,
                "custom_field_name" : "Ship Address 3",
                "export_field_order" : 7,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            },
            {
                "id" : None,
                "custom_field_name" : "Ship City",
                "export_field_order" : 8,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 18
            },
            {
                "id" : None,
                "custom_field_name" : "Ship State",
                "export_field_order" : 9,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 17
            },
            {
                "id" : None,
                "custom_field_name" : "Ship Zipcode",
                "export_field_order" : 10,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 22
            },
            {
                "id" : None,
                "custom_field_name" : "Ship Country",
                "export_field_order" : 11,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 28
            },
            {
                "id" : None,
                "custom_field_name" : "Tel",
                "export_field_order" : 12,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "226-268-0554",
                "configured_fields_id" : 43
            },
            {
                "id" : None,
                "custom_field_name" : "Shipping Method",
                "export_field_order" : 13,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "ePacket",
                "configured_fields_id" : 43
            },
            {
                "id" : None,
                "custom_field_name" : "SKU",
                "export_field_order" : 14,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 33
            },
            {
                "id" : None,
                "custom_field_name" : "Quantity",
                "export_field_order" : 15,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 39
            },
            {
                "id" : None,
                "custom_field_name" : "Item Total",
                "export_field_order" : 16,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            },
            {
                "id" : None,
                "custom_field_name" : "Shipping Fee",
                "export_field_order" : 17,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            },
            {
                "id" : None,
                "custom_field_name" : "Order Total",
                "export_field_order" : 18,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            },
            {
                "id" : None,
                "custom_field_name" : "Order Date",
                "export_field_order" : 19,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            },
            {
                "id" : None,
                "custom_field_name" : "Tracking Code",
                "export_field_order" : 20,
                "export_format_id" : None,
                "store_id_id" : None,
                "additional_header" : "",
                "custom_field_storage" : "",
                "configured_fields_id" : 31
            }
        ]
        elif layout_style == 2:
            self.layout_fields = [
        {
            "id" : None,
            "custom_field_name" : "Order Number",
            "export_field_order" : 0,
            "export_format_id" : 2,
            "store_id_id" : 2,
            "additional_header" : "订单号",
            "custom_field_storage" : "",
            "configured_fields_id" : 16
        },
        {
            "id" : None,
            "custom_field_name" : "Ship Name",
            "export_field_order" : 1,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "收件人",
            "custom_field_storage" : "",
            "configured_fields_id" : 21
        },
        {
            "id" : None,
            "custom_field_name" : "Tel",
            "export_field_order" : 2,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "收件人电话",
            "custom_field_storage" : "",
            "configured_fields_id" : 31
        },
        {
            "id" : None,
            "custom_field_name" : "Phone",
            "export_field_order" : 3,
            "export_format_id" : 2,
            "store_id_id" : 2,
            "additional_header" : "收件人手机",
            "custom_field_storage" : "226-268-0554",
            "configured_fields_id" : 43
        },
        {
            "id" : None,
            "custom_field_name" : "Address",
            "export_field_order" : 4,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "收件人地址",
            "custom_field_storage" : "",
            "configured_fields_id" : 44
        },
        {
            "id" : None,
            "custom_field_name" : "Zip ",
            "export_field_order" : 5,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "邮编",
            "custom_field_storage" : "",
            "configured_fields_id" : 22
        },
        {
            "id" : None,
            "custom_field_name" : "Country",
            "export_field_order" : 6,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "国家",
            "custom_field_storage" : "",
            "configured_fields_id" : 28
        },
        {
            "id" : None,
            "custom_field_name" : "State",
            "export_field_order" : 7,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "省",
            "custom_field_storage" : "",
            "configured_fields_id" : 17
        },
        {
            "id" : None,
            "custom_field_name" : "City",
            "export_field_order" : 8,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "市",
            "custom_field_storage" : "",
            "configured_fields_id" : 18
        },
        {
            "id" : None,
            "custom_field_name" : "Transportation Information",
            "export_field_order" : 9,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "配货信息",
            "custom_field_storage" : "ePacket",
            "configured_fields_id" : 43
        },
        {
            "id" : None,
            "custom_field_name" : "SKU",
            "export_field_order" : 10,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "品名",
            "custom_field_storage" : "",
            "configured_fields_id" : 33
        },
        {
            "id" : None,
            "custom_field_name" : "Quantity",
            "export_field_order" : 11,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "数量",
            "custom_field_storage" : "",
            "configured_fields_id" : 39
        },
        {
            "id" : None,
            "custom_field_name" : "Weight (g)",
            "export_field_order" : 12,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "重量G",
            "custom_field_storage" : "",
            "configured_fields_id" : 31
        },
        {
            "id" : None,
            "custom_field_name" : "Item Total",
            "export_field_order" : 13,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "价值USD",
            "custom_field_storage" : "",
            "configured_fields_id" : 31
        },
        {
            "id" : None,
            "custom_field_name" : "Shipping Fee",
            "export_field_order" : 14,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "备注",
            "custom_field_storage" : "",
            "configured_fields_id" : 31
        },
        {
            "id" : None,
            "custom_field_name" : "Order Total",
            "export_field_order" : 15,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "付款时间",
            "custom_field_storage" : "",
            "configured_fields_id" : 31
        },
        {
            "id" : None,
            "custom_field_name" : "Tracking Code",
            "export_field_order" : 16,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "店铺",
            "custom_field_storage" : "",
            "configured_fields_id" : 31
        },
        {
            "id" : None,
            "custom_field_name" : "Returns (Yes or No)",
            "export_field_order" : 17,
            "export_format_id" : None,
            "store_id_id" : None,
            "additional_header" : "退货（是或者否）",
            "custom_field_storage" : "",
            "configured_fields_id" : 31
        }
    ]


class DefaultCarrierMapping(object):
    def __init__(self):
        self.carrier_mapping = []

    def configure_carrier_mapping(self, carrier_defaults):
        if carrier_defaults == '(Default) ePacket and Registered Mail':
            self.carrier_mapping = [
            {
                "id" : None,
                "store_id_id" : None,
                "mapping_scheme": None,
                "mapped_carrier": 1,
                "shipping_country": 'AA',
                "tracking_url": "https://www.17track.net/en/track?nums="
            },
            {
                "id" : None,
                "store_id_id" : None,
                "mapping_scheme": None,
                "mapped_carrier": 29,
                "shipping_country": 'US',
                "tracking_url": None
            },
            {
                "id" : None,
                "store_id_id" : None,
                "mapping_scheme": None,
                "mapped_carrier": 8,
                "shipping_country": 'CA',
                "tracking_url": None
            },
            {
                "id" : None,
                "store_id_id" : None,
                "mapping_scheme": None,
                "mapped_carrier": 24,
                "shipping_country": 'GB',
                "tracking_url": None
            },
            {
                "id" : None,
                "store_id_id" : None,
                "mapping_scheme": None,
                "mapped_carrier": 1,
                "shipping_country": 'IE',
                "tracking_url": "https://track.anpost.ie/TrackingResults.aspx?rtt=0&site=website&trackcode="
            },
            {
                "id" : None,
                "store_id_id" : None,
                "mapping_scheme": None,
                "mapped_carrier": 6,
                "shipping_country": 'AU',
                "tracking_url": None
            },
            {
                "id" : None,
                "store_id_id" : None,
                "mapping_scheme": None,
                "mapped_carrier": 21,
                "shipping_country": 'NZ',
                "tracking_url": None
            },
            {
                "id" : None,
                "store_id_id" : None,
                "mapping_scheme": None,
                "mapped_carrier": 22,
                "shipping_country": 'SE',
                "tracking_url": None
            }
        ]
