#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MOM SQL Client
"""

from ConfigParser import SafeConfigParser, Error
from datetime import date
import logging
import os
from pymssql import connect, InterfaceError


class MOMClient(object):
    """ MOM SQL Client """

    CC_TYPES = {'MC': 'MasterCard',
                'VI': 'Visa',
                'DI': 'Discover',
                'AM': 'American Express',
                'DU': 'Manual'}

    def __init__(self):
        self.conn = None

    def get_mom_connection(self):
        """ Gets SQL Server connection to MOM """
        config = SafeConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        try:
            momdb_host = config.get("momdb", "host")
            momdb_user = config.get("momdb", "user")
            momdb_password = config.get("momdb", "password")
            momdb_db = config.get("momdb", "db")
        except Error as error:
            msg = "Config section [momdb] bad or missing: %s" % error.message
            logging.error(msg)
            raise Exception(msg)

        try:
            logging.info('Connecting to MOM...')
            if self.conn is None:
                self.conn = connect(host=momdb_host, user=momdb_user,
                                    password=momdb_password,
                                    database=momdb_db, as_dict=True)
            return self.conn
        except InterfaceError as error:
            msg = "Error connecting to SQL Server: %s" % error.message
            logging.error(msg)
            raise Exception(msg)
        except Error as error:
            logging.error(error.message)
            raise

    def get_new_orders(self):
        """
        Get new orders from MOM by calling sproc "Emailer_GetNewOrders"
        """
        orders_dict = {}
        try:
            conn = self.get_mom_connection()
            cur = conn.cursor()
            cur.callproc("EmailVision_GetNewOrders")
            for row in cur:
                logging.debug("CUSTNUM=%d, FIRSTNAME=%s" % (
                    row['CUSTNUM'], row['FIRSTNAME']))
                order = Order(row)
                if order in orders_dict:
                    orders_dict[order].append(order)
                else:
                    orders_dict[order] = [order]
            # conn.close()
        except Error as error:
            logging.error(error.message)
            raise

        orders_list = self.normalize_orders_dict(orders_dict)

        return orders_list

    def get_upcoming_autoship_orders(self):
        """ Gets upcoming Autoship orders for prenotice email """
        orders_dict = {}
        try:
            conn = self.get_mom_connection()
            cur = conn.cursor()
            cur.callproc("GetAutoShipPreNotice")
            for row in cur:
                logging.debug("CUSTNUM=%d, FIRSTNAME=%s" % (
                    row['CUSTNUM'], row['FIRSTNAME']))
                order = Order(row)
                if order in orders_dict:
                    orders_dict[order].append(order)
                else:
                    orders_dict[order] = [order]
            # conn.close()
        except Error as error:
            logging.error(error.message)
            raise

        orders_list = self.normalize_orders_dict(orders_dict)

        return orders_list

    def get_backorders(self):
        """ Gets backorders for notice email """
        orders_dict = {}
        try:
            conn = self.get_mom_connection()
            cur = conn.cursor()
            cur.callproc("EmailVision_GetBackOrders")
            for row in cur:
                order = Order(row)
                if order in orders_dict:
                    orders_dict[order].append(order)
                else:
                    orders_dict[order] = [order]
        except Error as error:
            logging.error(error.message)
            raise
        orders_list = self.normalize_orders_dict(orders_dict)
        return orders_list

    def get_shipped_orders(self):
        """ Gets shipped orders for notice email """
        orders_dict = {}
        try:
            conn = self.get_mom_connection()
            cur = conn.cursor()
            cur.callproc("EmailVision_GetShipped")
            for row in cur:
                order = Order(row)
                if order in orders_dict:
                    orders_dict[order].append(order)
                else:
                    orders_dict[order] = [order]
        except Error as error:
            logging.error(error.message)
            raise
        orders_list = self.normalize_orders_dict(orders_dict)
        return orders_list

    def normalize_orders_dict(self, orders_dict):
        """ normalize orders into Order->OrderItems """
        orders_list = []
        for orders in orders_dict:
            # some orders have >1 "order" (line item)
            for order_line in orders_dict[orders]:
                order_item = OrderItem()
                order_item.sku = order_line.sku
                order_item.description = order_line.description
                order_item.discount = order_line.discount
                order_item.qty = order_line.qty
                order_item.list_price = order_line.list_price
                order_item.total = order_line.list_price * order_line.qty
                orders.order_items.append(order_item)
                logging.info("Order %s\tItem %s" %
                            (order_line.order_num, order_item.sku))

        for order in orders_dict:
            logging.info("Order %s has %d line items: %s" %
                         (order.order_num,
                          len(order.order_items),
                          order.order_items))
            order.subtotal = \
                float(order.total) - \
                float(order.tax) - \
                float(order.shipping_fee) - \
                float(order.discount) - \
                float(order.promocode_discount)
            orders_list.append(order)
        return orders_list


class Order(object):
    """ Order """
    def __init__(self, row=None):
        if row is None:
            self.order_num = ''
            self.cust_num = ''
            self.first_name = ''
            self.last_name = ''
            self.email = ''
            self.expect_ship = date.max
            self.billing_address1 = ''
            self.billing_address2 = ''
            self.billing_city = ''
            self.billing_state = ''
            self.billing_zip = ''
            self.discount = 0.00
            self.payment_type = ''
            self.sku = ''
            self.description = ''
            self.list_price = ''
            self.unit_price = ''
            self.ext_price = ''
            self.order_date = date.min
            self.qty = 0
            self.payment_last4 = ''
            self.tax = 0.00
            self.shipping_fee = 0.00
            self.subtotal = 0.00
            self.total = 0.00
            self.promocode = ''
            self.promocode_discount = 0.00
            self.shipping_address1 = ''
            self.shipping_address2 = ''
            self.shipping_city = ''
            self.shipping_state = ''
            self.shipping_zip = ''
            self.ship_type = ''
            self.tracking_num = ''
            self.tracking_url = ''
            self.source_key = ''
            self.order_items = []
        else:
            self.order_num = int(row['ORDERNO'])
            self.cust_num = row.get('CUSTNUM', '')
            self.first_name = row['FIRSTNAME']
            self.last_name = row.get('LASTNAME', '')
            self.email = 'roger.braun@nutrihealth.com'  # row['EMAIL']
            self.expect_ship = row.get('SHIP_DATE', date.max)
            if self.expect_ship == date.max:
                self.expect_ship = row.get('NEXT_SHIP', date.max)
            self.billing_address1 = row.get('ADDR', '')
            self.billing_address2 = row.get('ADDR2', '')
            self.billing_city = row.get('CITY', '')
            self.billing_state = row.get('STATE', '')
            self.billing_zip = row.get('ZIPCODE', '')
            self.discount = row.get('DISCOUNT', 0.00)
            self.payment_type = \
                MOMClient.CC_TYPES.get(row.get('CARDTYPE', ''), 'Other')
            self.payment_last4 = ''
            self.sku = row.get('ITEM', '')
            self.description = row.get('DESC1', '')
            self.list_price = row.get('IT_UNLIST', 0)
            self.unit_price = ''
            self.ext_price = ''
            self.order_date = row.get('ODR_DATE', date.min)
            self.qty = row.get('QUANTO', 0)
            self.tax = row.get('TAX', 0)
            self.shipping_fee = row.get('SHIPPING', 0)
            self.subtotal = row.get('ORD_TOTAL', 0)
            self.total = row.get('ORD_TOTAL', 0)
            self.promocode = 'Not Available'
            self.promocode_discount = 0.00
            self.shipping_address1 = row.get('ADDR', '')
            self.shipping_address2 = row.get('ADDR2', '')
            self.shipping_city = row.get('CITY', '')
            self.shipping_state = row.get('STATE', '')
            self.shipping_zip = row.get('ZIPCODE', '')
            self.ship_type = ''
            self.tracking_num = row.get('TRACKINGNO', 'Not Available')
            if self.tracking_num == '':
                self.tracking_num = 'Not Available'
            self.tracking_url = ''
            self.source_key = row.get('SourceKey', 'Not Available')
            if self.source_key == '':
                self.source_key = 'Not Available'
            self.order_items = []

    def __hash__(self):
        return hash(self.order_num)

    def __eq__(self, other):
        return self.order_num == other.order_num

    def html_table(self):
        """ Returns order as a collection of HTML rows """
        table = ""
        for order_item in self.order_items:
            table += (
                "  <tr>"
                "    <td>" + order_item.sku + "</td>"
                "    <td>" + order_item.description + "</td>"
                "    <td>" + str(order_item.qty) + "</td>"
                "    <td>" + "$%0.2f" % order_item.list_price + "</td>"
                "    <td>" + "$%0.2f" % order_item.total + "</td>"
                "  </tr>")
        logging.debug(table)
        return table

    def html_table_autoship(self):
        """ Returns order as a collection of HTML rows """
        table = ""
        for order_item in self.order_items:
            table += (
                "  <tr>"
                "    <td>" + order_item.sku + "</td>"
                "    <td>" + order_item.description + "</td>"
                "    <td>" + str(order_item.qty) + "</td>"
                "    <td>" + "$%0.2f" % order_item.list_price + "</td>"
                "    <td>" + "$%0.2f" % order_item.total + "</td>"
                "  </tr>")
        logging.debug(table)
        return table


class OrderItem(object):
    """ Order Item  """
    def __init__(self, row=None):
        if row is None:
            self.order_num = ''
            self.expect_ship = date.today()
            self.sku = ''
            self.description = ''
            self.list_price = ''
            self.unit_price = ''
            self.ext_price = ''
            self.discount = 0.00
            self.qty = 0
            self.tax = 0.00
            self.shipping = 0.00
            self.ship_type = ''
            self.tracking_num = ''
            self.tracking_url = ''
            self.source_key = ''
            self.total = 0.00
        else:
            self.order_num = row['ORDERNO']
            self.expect_ship = row['NEXT_SHIP']
            self.sku = row['ITEM']
            self.description = row['DESC1']
            self.discount = float(row['DISCOUNT'])
            self.list_price = float(row['IT_UNLIST'])
            self.unit_price = float(row['IT_UNLIST'])
            self.ext_price = float(row['IT_UNLIST'])
            self.qty = int(row['QUANTO'])
            self.tax = float(row['TAX'])
            self.shipping = float(row['SHIPPING'])
            self.ship_type = ''
            self.tracking_num = row.get('TRACKINGNO', 'Not Available')
            self.tracking_url = ''
            self.source_key = row['SourceKey']
            self.total = self.qty * self.list_price

    def html_row(self):
        """ Returns order item as an HTML row """
        row = ("  <tr>"
               "    <td>" + self.sku + "</td>"
               "    <td>" + self.description + "</td>"
               "    <td>" + str(self.qty) + "</td>"
               "    <td>" + "$%0.2f" % self.list_price + "</td>"
               "    <td>" + "$%0.2f" % self.total + "</td>"
               "  </tr>")
        logging.debug(row)
        return row

if __name__ == '__main__':
    pass
