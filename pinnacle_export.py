#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Use Pinnacle Cart API to export product catalog for consumption by Magento.
"""

import argparse
from ConfigParser import ConfigParser, Error
import csv
import glob
import logging
import os
import requests
import sys
import json
from pymssql import connect, InterfaceError
from xlsxwriter.workbook import Workbook

LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

Config = ConfigParser()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-l',
        type=str,
        default='info',
        help="logging level. Default is info. Use debug if you have problems."
    )
    parser.add_argument(
        '-f',
        type=str,
        default='pinnacle_export.log',
        help='logging file. Default is pinnacle_export.log.'
    )
    args = parser.parse_args()
    logging_level = LOGGING_LEVELS.get(args.l, logging.NOTSET)
    logging.basicConfig(level=logging_level, filename=args.f,
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
    r = requests.get(
        'https://www.nutri-health.com/content/admin/plugins/openapi/index.php',
        params=payload)
    #print r.status_code
    #print r.text
    j = json.loads(r.text, encoding='ascii')
    product_import_csv(j)
    export_to_excel()
    sys.exit(0)


def product_import_csv(data):
    with open('PRODUCT-IMPORT.csv', 'w') as csvfile:
        csv.field_size_limit(1000000000)
        writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL, doublequote=True)
        writer.writerow(['sku', 'name', 'product.type',
                         'product.attribute_set',
                         'product.has_options', 'product.required_options',
                         'status', 'visibility', 'price', 'short_description',
                         'description', 'tax_class_id', 'weight',
                         'category.path', 'special_price', 'image',
                         'small_image', 'thumbnail', 'stock.qty'])

        for d in data:
            print d["Product"]["Title"].encode('utf-8')
            writer.writerow([
                d["Product"]["Sku"],  # sku
                d["Product"]["Title"].encode('utf8'),  # name
                'simple',  # product.type
                'Default',  # product.attribute_set
                'No',  # product.has_options
                'No',  # product.required_options
                'Enabled',  # product.status
                'Catalog, Search',  # product.visibility
                d["Product"]["Price"],  # product.price
                # product.short_description
                d["Product"]["Description"].replace('\r\n', '').encode(
                    'utf8')[0:255],
                # product.description
                d["Product"]["Description"].replace(
                    '\r\n', ''
                ).encode('utf8')[0:8000],
                'Taxable Goods',  # tax_class_id
                d["Product"]["Weight"],  # weight
                get_category_path(d["Product"]["CategoryName"]),
                # category.path
                '',  # special_price
                d["Product"]["ImageUrl"],  # image
                '',  # small_image
                d["Product"]["ThumbnailImageUrl"],  # thumbnail
                get_stock_qty(d["Product"]["Sku"])  # stock.qty
            ])


def get_category_path(category_name):
    # print category_name
    #return category_name
    return ''


def export_to_excel():
    for csvfile in glob.glob(os.path.join('.', '*.csv')):
        workbook = Workbook(csvfile.replace('.csv', '') + '.xlsx')
        worksheet = workbook.add_worksheet()
        with open(csvfile, 'rb') as f:
            reader = csv.reader(f)
            for r, row in enumerate(reader):
                for c, col in enumerate(row):
                    worksheet.write(r, c, unicode(col, "utf8"))
        workbook.close()


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
        conn = connect(host=momdb_host, user=momdb_user,
                       password=momdb_password,
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
