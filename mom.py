#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MOM SQL Client
"""

from ConfigParser import SafeConfigParser, Error
from datetime import date
import logging
from pymssql import connect, InterfaceError


class MOMClient(object):
    """ MOM SQL Client """
    def __init__(self):
        pass

    def get_mom_connection(self):
        """ Gets SQL Server connection to MOM """
        config = SafeConfigParser()
        config.read('config.ini')

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
            conn = connect(host=momdb_host, user=momdb_user,
                           password=momdb_password,
                           database=momdb_db, as_dict=True)
            return conn
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
        orders = []
        try:
            conn = self.get_mom_connection()
            cur = conn.cursor()
            cur.callproc("Emailer_GetNewOrders")
            for row in cur:
                logging.debug("CUSTNUM=%d, FIRSTNAME=%s" % (
                    row['CUSTNUM'], row['FIRSTNAME']))
                order = Order(row)
                orders.append(order)
            conn.close()
        except Error as error:
            logging.error(error.message)
            raise
        return orders

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
                # logging.info("Order %s" % orders_dict[order])
            conn.close()
        except Error as error:
            logging.error(error.message)
            raise

        # normalize orders into Order->OrderItems
        for orders in orders_dict:
            # some orders have >1 "order" (line item)
            for order in orders_dict[orders]:
                order_item = OrderItem()
                order_item.sku = order.sku
                order_item.description = order.description
                order_item.qty = order.qty
                order_item.list_price = order.list_price
                order_item.total = order.total
                order.order_items.append(order_item)
                logging.debug(order.html_table())

        return orders_dict.keys()

    def get_backorders(self):
        """ Gets backorders for notice email """
        # TODO get_backorders
        orders = []
        order = Order()
        orders.append(order)
        return orders


class Order(object):
    """ Order """
    def __init__(self, row=None):
        if row is None:
            self.order_num = ''
            self.cust_num = ''
            self.first_name = ''
            self.last_name = ''
            self.email = ''
            self.expect_ship = date.today()
            self.billing_address1 = ''
            self.billing_address2 = ''
            self.billing_city = ''
            self.billing_state = ''
            self.billing_zip = ''
            self.discount = 0.00
            self.payment_type = ''
            self.payment_last4 = ''
            self.sku = ''
            self.description = ''
            self.list_price = ''
            self.unit_price = ''
            self.ext_price = ''
            self.qty = 0
            self.tax = 0.00
            self.shipping_fee = 0.00
            self.subtotal = 0.00
            self.total = 0.00
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
            self.cust_num = row['CUSTNUM']
            self.first_name = row['FIRSTNAME']
            self.last_name = row['LASTNAME']
            self.email = row['EMAIL']
            self.expect_ship = row['NEXT_SHIP']
            self.billing_address1 = ''
            self.billing_address2 = ''
            self.billing_city = ''
            self.billing_state = ''
            self.billing_zip = ''
            self.discount = 0.00
            self.payment_type = ''
            self.payment_last4 = ''
            self.sku = row['ITEM']
            self.description = row['DESC1']
            self.list_price = row.get('IT_UNLIST', 0)
            self.unit_price = ''
            self.ext_price = ''
            self.qty = row['QUANTO']
            self.tax = row.get('TAX', 0)
            self.shipping_fee = row.get('SHIPPING', 0)
            self.subtotal = row.get('ORD_TOTAL', 0)
            self.total = row.get('ORD_TOTAL', 0)
            self.promocode_discount = 0.00
            self.shipping_address1 = ''
            self.shipping_address2 = ''
            self.shipping_city = ''
            self.shipping_state = ''
            self.shipping_zip = ''
            self.ship_type = ''
            self.tracking_num = ''
            self.tracking_url = ''
            self.source_key = row['SourceKey']
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
                "    <td>" + "%0.2f" % order_item.list_price + "</td>"
                "    <td>" + str(order_item.total) + "</td>"
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
            self.list_price = row['IT_UNLIST']
            self.unit_price = ''
            self.ext_price = ''
            self.qty = row['QUANTO']
            self.tax = row['TAX']
            self.shipping = row['SHIPPING']
            self.ship_type = ''
            self.tracking_num = ''
            self.tracking_url = ''
            self.source_key = row['SourceKey']
            self.total = 0.00

    def html_row(self):
        """ Returns order item as an HTML row """
        s = ("  <tr>"
             "    <td>" + self.sku + "</td>"
             "    <td>" + self.description + "</td>"
             "    <td>" + str(self.qty) + "</td>"
             "    <td>" + "%0.2f" % self.list_price + "</td>"
             "    <td>" + str(self.total) + "</td>"
             "  </tr>")
        logging.debug(s)
        return s

if __name__ == '__main__':
    pass
