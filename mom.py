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
            exit(msg)

        try:
            logging.info('Connecting to MOM...')
            conn = connect(host=momdb_host, user=momdb_user,
                           password=momdb_password,
                           database=momdb_db, as_dict=True)
            return conn
        except InterfaceError as error:
            msg = "Error connecting to SQL Server: %s" % error.message
            logging.error(msg)
            exit(msg)
        except Error as error:
            logging.error(error.message)
            exit(error.message)

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
            exit(error.message)
        return orders

    def get_upcoming_autoship_orders(self):
        """ Gets upcoming Autoship orders for prenotice email """
        orders = []
        try:
            conn = self.get_mom_connection()
            cur = conn.cursor()
            cur.callproc("GetAutoShipPreNotice")
            for row in cur:
                logging.debug("CUSTNUM=%d, FIRSTNAME=%s" % (
                    row['CUSTNUM'], row['FIRSTNAME']))
                order = Order(row)
                orders.append(order)
            conn.close()
        except Error as error:
            logging.error(error.message)
            exit(error.message)
        return orders

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
            self.sku = ''
            self.description = ''
            self.list_price = ''
            self.unit_price = ''
            self.ext_price = ''
            self.qty = 0
            self.tax = 0
            self.shipping = 0
            self.total = 0
            self.ship_type = ''
            self.tracking_num = ''
            self.tracking_url = ''
            self.source_key = ''
            self.order_items = []
        else:
            self.order_num = row['ORDERNO']
            self.cust_num = row['CUSTNUM']
            self.first_name = row['FIRSTNAME']
            self.last_name = row['LASTNAME']
            self.email = row['EMAIL']
            self.expect_ship = row['NEXT_SHIP']
            self.sku = row['ITEM']
            self.description = row['DESC1']
            self.list_price = row.get('IT_UNLIST', 0)
            self.unit_price = ''
            self.ext_price = ''
            self.qty = row['QUANTO']
            self.tax = row.get('TAX', 0)
            self.shipping = row.get('SHIPPING', 0)
            self.total = row.get('ORD_TOTAL', 0)
            self.ship_type = ''
            self.tracking_num = ''
            self.tracking_url = ''
            self.source_key = row['SourceKey']
            self.order_items = []

    def html_table(self):
        """ Returns order as a collection of HTML rows """
        s = ("  <tr>"
             "    <td>" + self.sku + "</td>"
             "    <td>" + self.description + "</td>"
             "    <td>" + str(self.qty) + "</td>"
             "    <td>" + "%0.2f" % self.list_price + "</td>"
             "    <td>" + str(self.total) + "</td>"
             "  </tr>")
        logging.debug(s)
        return s


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
