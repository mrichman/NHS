#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Use Pinnacle Cart API to export product catalog for consumption by Magento.
"""

from ConfigParser import ConfigParser, Error
import logging
from optparse import OptionParser
import sys
import requests
import csv
import json
from pymssql import connect, InterfaceError

LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

Config = ConfigParser()


def main():
    parser = OptionParser()
    parser.add_option('-l', '--logging-level', help='Logging level')
    parser.add_option('-f', '--logging-file', help='Logging file name')
    (options, args) = parser.parse_args()
    logging_level = LOGGING_LEVELS.get(options.logging_level, logging.NOTSET)
    logging.basicConfig(level=logging_level, filename=options.logging_file,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    try:
        Config.read("config.ini")
    except Error:
        msg = "config.ini file bad or missing"
        logging.error(msg)
        exit(msg)

    try:
        pcapi_username = Config.get("pcapi", "username")
        pcapi_password = Config.get("pcapi", "password")
        pcapi_token = Config.get("pcapi", "password")
    except Error:
        msg = "Config section [pcapi] bad or missing"
        logging.error(msg)
        exit(msg)

    payload = {'username': pcapi_username, 'password': pcapi_password,
               'token': pcapi_token, 'apiType': 'json', 'call': 'GetProducts',
               'PrimaryCategory': -1}
    r = requests.get('https://www.nutri-health.com/content/admin/plugins/openapi/index.php', params=payload)
    #print r.status_code
    #print r.text
    j = json.loads(r.text, encoding='ascii')
    product_import_csv(j)
    sys.exit(0)


def product_import_csv(data):
    with open('PRODUCT-IMPORT.csv', 'w') as csvfile:
        csv.field_size_limit(1000000000)
        writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL, doublequote=True)
        writer.writerow(['sku', 'name', 'product.type', 'product.attribute_set', 'product.has_options',
                         'product.required_options', 'status', 'visibility', 'price', 'short_description',
                         'description',
                         'tax_class_id', 'weight', 'category.path', 'special_price', 'image', 'small_image',
                         'thumbnail', 'stock.qty'])
                         # 'url_key', 'servings_per_container', 'serving_size', 'dosage_double', 'guarantee',
                         # 'meta_description', 'meta_keyword', 'meta_title', 'allow_message', 'allow_open_amount',
                         # 'aw_sarp_anonymous_subscription', 'aw_sarp_display_calendar', 'aw_sarp_download_by_status',
                         # 'aw_sarp_enabled', 'aw_sarp_exclude_to_group', 'aw_sarp_first_period_price',
                         # 'aw_sarp_has_shipping', 'aw_sarp_include_to_group', 'aw_sarp_options_to_first_price',
                         # 'aw_sarp_period', 'aw_sarp_shipping_cost', 'aw_sarp_subscription_price', 'color', 'cost',
                         # 'country_of_manufacture', 'created_at', 'custom_design', 'custom_design_from',
                         # 'custom_design_to',
                         # 'custom_layout_update', 'delivery_method', 'email_template', 'enable_googlecheckout',
                         # 'gender_specific', 'giftcard_amounts', 'giftcard_type', 'gift_message_available',
                         # 'gift_wrapping_available', 'gift_wrapping_price', 'group_price', 'image_label', 'is_recurring',
                         # 'is_redeemable', 'is_returnable', 'lifetime', 'links_exist', 'links_purchased_separately',
                         # 'links_title', 'manufacturer', 'msrp', 'msrp_display_actual_price_type', 'msrp_enabled',
                         # 'news_from_date', 'news_to_date', 'old_id', 'open_amount_max', 'open_amount_min',
                         # 'options_container', 'page_layout', 'price_type', 'price_view', 'products_size',
                         # 'prop_65_product', 'recurring_profile', 'refrigeration_recommendation',
                         # 'related_tgtr_position_behavior', 'related_tgtr_position_limit', 'samples_title',
                         # 'shipment_type',
                         # 'sku_type', 'small_image_label', 'special_from_date', 'special_to_date', 'thumbnail_label',
                         # 'tier_price', 'upc', 'updated_at', 'upsell_tgtr_position_behavior',
                         # 'upsell_tgtr_position_limit',
                         # 'url_path', 'use_config_allow_message', 'use_config_email_template',
                         # 'use_config_is_redeemable',
                         # 'use_config_lifetime', 'video', 'weight_type', 'product.websites', 'category.ids',
                         # 'category.name', 'stock.is_in_stock', 'stock.backorders', 'stock.manage_stock',
                         # 'stock.use_config_manage_stock', 'stock.is_qty_decimal', 'stock.use_config_notify_stock_qty',
                         # 'stock.use_config_min_qty', 'stock.use_config_backorders', 'stock.use_config_min_sale_qty',
                         # 'stock.use_config_max_sale_qty', 'stock.stock_status_changed_automatically',
                         # 'stock.use_config_enable_qty_increments', 'stock.enable_qty_increments',
                         # 'stock.use_config_qty_increments', 'stock.qty', 'stock.min_qty', 'stock.min_sale_qty',
                         # 'stock.max_sale_qty', 'stock.notify_stock_qty', 'stock.qty_increments',
                         # 'product.configurable_parent_sku', 'price.final', 'price.minimal', 'price.maximum'])

        for d in data:
            # print d["Product"]
            # print d["Product"]["Sku"]
            print d["Product"]["Title"].encode('utf-8')
            writer.writerow([d["Product"]["Sku"],                                # sku
                             d["Product"]["Title"].encode('utf8'),               # name
                             'simple',                                           # product.type
                             '',                                                 # product.attribute_set
                             'No',                                               # product.has_options
                             'No',                                               # product.required_options
                             'Enabled',                                          # product.status
                             'Catalog,Search',                                   # product.visibility
                             d["Product"]["Price"],                              # product.price
                             d["Product"]["Description"].replace('\r\n', '').encode('utf8')[0:255],   # product.short_description
                             d["Product"]["Description"].replace('\r\n', '').encode('utf8')[0:8000],  # product.description
                             'Taxable Goods',                                    # tax_class_id
                             d["Product"]["Weight"],                             # weight
                             get_category_path(d["Product"]["CategoryName"]),         # category.path
                             '',                                                 # special_price
                             d["Product"]["ImageUrl"],                           # image
                             '',                                                 # small_image
                             d["Product"]["ThumbnailImageUrl"],                  # thumbnail
                             get_stock_qty(d["Product"]["Sku"])])                # stock.qty


def get_category_path(category_name):
    # print category_name
    pass


def get_stock_qty(sku):
    try:
        momdb_host = Config.get("momdb", "host")
        momdb_user = Config.get("momdb", "user")
        momdb_password = Config.get("momdb", "password")
        momdb_db = Config.get("momdb", "db")
    except Error:
        msg = "Config section [momdb] bad or missing"
        logging.error(msg)
        exit(msg)

    try:
        conn = connect(host=momdb_host, user=momdb_user, password=momdb_password,
                       database=momdb_db)
        cur = conn.cursor()
        cur.execute("SELECT units from stock where number = '" + sku + "'")
        row = cur.fetchone()
        qty = int(row[0])
        conn.close()
        return qty
    except InterfaceError as error:
        msg = "Error connecting to SQL Server: %s" % error.message
        logging.error(msg)
        exit(msg)


if __name__ == '__main__':
    main()


