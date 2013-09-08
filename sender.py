#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EmailVision Transactional Email API Integration

This application pulls the following data from MOM and sends via SOAP request
to EmailVision:

* Order Confirmation
* Autoship Pre-Shipment Notice
* Shipping Confirmation
* Backorder Notice
* Blog Subscription Success Email
* Blog Unsubscribe Success Email
* Customer Feedback survey
* Shopping Cart Abandonment Email 20-minute delay
* Shopping Cart Abandonment Email 24-hour delay

"""

import argparse
import logging
import sqlite3
from ConfigParser import SafeConfigParser, Error
from datetime import date
from pymssql import connect, InterfaceError
from time import strftime

from suds.client import Client
from pinnacle import PinnacleClient

LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

WSDL_URL = \
    'http://api.notificationmessaging.com/NMSOAP/NotificationService?wsdl'

TEMPLATES = {"[EMV] Test": 15367,
             "Trigger_OrderShipment1": 1532948,
             "Trigger_OrderAckknowledge1": 1532947,
             "TEST-Drift-Trigger1": 1531070,
             "Autoship-Prenotice": 1536856,
             "Backorder-Notice": 1536855}

RANDOMTAGS = {"[EMV] Test": 'FA6100040001FF8C',
              "Trigger_OrderShipment1": '952110747E020009',
              "Trigger_OrderAckknowledge1": '9D1F8080000474AA',
              "TEST-Drift-Trigger1": '608D795E7C020060',
              "Autoship-Prenotice": '76FC140010000D9E',
              "Backorder-Notice": '1E78EC9828002001'}

MAILINGS = ['order-conf', 'ship-conf', 'as-prenotice', 'backorder', 'blog-sub',
            'blog-unsub', 'cust-survey', 'cart-abandon-20m',
            'cart-abandon-24h', 'test-email']


def create_request():
    """ Creates EmailVision SOAP Request Client """
    client = Client(WSDL_URL)
    return client.factory.create('sendRequest')


def send_object(request):
    """ Sends SOAP Request """
    logging.info("Sending SOAP request...")
    client = Client(WSDL_URL)
    return client.service.sendObject(request)


def main():
    """ Main function """
    parser = argparse.ArgumentParser(description="EmailVision Sender")
    parser.add_argument(
        '-l',
        type=str,
        default='info',
        help="logging level. Default is info. Use debug if you have problems."
    )
    parser.add_argument(
        '-f',
        default='sender.log',
        help='logging file. Default is sender.log.'
    )
    parser.add_argument(
        '-m',
        required=True,
        help=('Mailing to invoke. One of %s' % MAILINGS)
    )
    args = parser.parse_args()

    if args.m not in MAILINGS:
        print('Mailing must be one of %s' % MAILINGS)
        exit(1)

    logging_level = LOGGING_LEVELS.get(args.l, logging.INFO)
    logging.basicConfig(level=logging_level, filename=args.f,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger().setLevel(logging_level)
    logging.getLogger('suds.client').setLevel(logging_level)
    # console handler with specified log level
    ch = logging.StreamHandler()
    ch.setLevel(logging_level)
    logging.getLogger().addHandler(ch)

    setup_sqlite()

    if args.m == 'order-conf':
        order_conf()
    elif args.m == 'test-email':
        test_email()
    elif args.m == 'ship-conf':
        ship_confirmation()
    elif args.m == 'as-prenotice':
        autoship_prenotice()
    elif args.m == 'cart-abandon-20m':
        cart_abandon_20m()
    elif args.m == 'cart-abandon-24h':
        cart_abandon_24h()
    elif args.m == 'backorder':
        backorder_notice()


def test_email():
    """ Send test email """
    order = Order()
    order.first_name = 'Jan'
    order.last_name = 'Alexander'
    order.email = 'jealexander6861@gmail.com'
    order.sku = '10400'
    order.description = 'Flora Source 60 ct'
    order.cust_num = 5173525
    order.list_price = 33.00
    order.order_num = 838513
    order.qty = 3
    order.total = 99.00
    order.tax = 0.00
    req = create_request()
    req.dyn = [
        {
            'entry': [
                {"key": 'FIRSTNAME', 'value': order.first_name}
            ]
        }
    ]
    req.content = [
        {
            'entry': [
                {'key': 1, 'value': order.html_table()}
            ]
        }
    ]
    req.email = 'mark.richman@nutri-health.com'
    config = SafeConfigParser()
    config.read('config.ini')
    req.encrypt = config.get("emailvision", "order_conf_key")
    req.notificationId = TEMPLATES["Trigger_OrderAckknowledge1"]
    req.random = RANDOMTAGS["Trigger_OrderAckknowledge1"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    if not was_mail_sent(req.email, req.notificationId):
        res = send_object(req)
        logging.debug(res)
        record_sent_mail(req.email, req.notificationId)
    else:
        logging.info("Mail already sent. Skipping.")


def ship_confirmation():
    """ Ship Confirmation Email """
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    config = SafeConfigParser()
    config.read('config.ini')
    req.encrypt = config.get("emailvision", "ship_conf_key")
    req.notificationId = TEMPLATES["Trigger_OrderShipment1"]
    req.random = RANDOMTAGS["Trigger_OrderShipment1"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    if not was_mail_sent(req.email, req.notificationId):
        res = send_object(req)
        logging.debug(res)
        record_sent_mail(req.email, req.notificationId)
    else:
        logging.debug("Mail already sent. Skipping.")


def order_conf():
    """ Order Confirmation Email """
    orders = get_new_orders()
    logging.info("Got %d orders from MOM." % len(orders))
    for order in orders:
        req = create_request()
        req.dyn = [
            {
                'entry': [
                    {"key": 'FIRSTNAME', 'value': order.first_name}
                ]
            }
        ]
        req.content = [
            {
                'entry': [
                    {'key': 1, 'value': order.html_table()}
                ]
            }
        ]
        # TODO set req.email = customer's email
        req.email = 'mark.richman@nutrihealth.com'
        config = SafeConfigParser()
        config.read('config.ini')
        req.encrypt = config.get("emailvision", "order_conf_key")
        req.notificationId = TEMPLATES["Trigger_OrderAckknowledge1"]
        req.random = RANDOMTAGS["Trigger_OrderAckknowledge1"]
        req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
        req.synchrotype = 'NOTHING'
        req.uidkey = 'email'
        if not was_mail_sent(req.email, req.notificationId, order.order_num):
            res = send_object(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId, order.order_num)
        else:
            logging.debug("Mail already sent. Skipping.")


def cart_abandon_20m():
    """ Cart Abandonment Email """
    client = PinnacleClient()
    carts = client.get_abandoned_carts()
    config = SafeConfigParser()
    config.read('config.ini')
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    req.encrypt = config.get("emailvision", "cart_abandon_key")
    req.notificationId = TEMPLATES["TEST-Drift-Trigger1"]
    req.random = RANDOMTAGS["TEST-Drift-Trigger1"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    if not was_mail_sent(req.email, req.notificationId):
        res = send_object(req)
        logging.debug(res)
        record_sent_mail(req.email, req.notificationId)
    else:
        logging.debug("Mail already sent. Skipping.")

def cart_abandon_24h():
    """ Cart Abandonment Email """
    client = PinnacleClient()
    carts = client.get_abandoned_carts()
    config = SafeConfigParser()
    config.read('config.ini')
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    req.encrypt = config.get("emailvision", "cart_abandon_key")
    req.notificationId = TEMPLATES["TEST-Drift-Trigger1"]
    req.random = RANDOMTAGS["TEST-Drift-Trigger1"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    if not was_mail_sent(req.email, req.notificationId):
        res = send_object(req)
        logging.debug(res)
        record_sent_mail(req.email, req.notificationId)
    else:
        logging.debug("Mail already sent. Skipping.")


def autoship_prenotice():
    """ Autoship Prenotice Email """
    orders = get_upcoming_autoship_orders()
    logging.info("Got %d orders from MOM." % len(orders))
    for order in orders:
        req = create_request()
        req.dyn = [
            {
                'entry': [
                    {"key": 'FIRSTNAME', 'value': order.first_name}
                ]
            }
        ]
        req.content = [
            {
                'entry': [
                    {'key': 1, 'value': order.html_table()}
                ]
            }
        ]
        # TODO set req.email = customer's email
        req.email = 'mark.richman@nutrihealth.com'
        config = SafeConfigParser()
        config.read('config.ini')
        req = create_request()
        req.email = 'mark.richman@nutrihealth.com'
        req.encrypt = config.get("emailvision", "as_prenotice_key")
        req.notificationId = TEMPLATES["Autoship-Prenotice"]
        req.random = RANDOMTAGS["Autoship-Prenotice"]
        req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
        req.synchrotype = 'NOTHING'
        req.uidkey = 'email'
        if not was_mail_sent(req.email, req.notificationId, order.order_num):
            res = send_object(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId, order.order_num)
        else:
            logging.debug("Mail already sent. Skipping.")


def backorder_notice():
    """ Backorder Notice Email """
    orders = get_backorders()
    # TODO iterate through orders and generate emails
    config = SafeConfigParser()
    config.read('config.ini')
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    req.encrypt = config.get("emailvision", "backorder_notice_key")
    req.notificationId = TEMPLATES["Backorder-Notice"]
    req.random = RANDOMTAGS["Backorder-Notice"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    if not was_mail_sent(req.email, req.notificationId):
        res = send_object(req)
        logging.debug(res)
        record_sent_mail(req.email, req.notificationId)
    else:
        logging.debug("Mail already sent. Skipping.")


def get_upcoming_autoship_orders():
    """ Gets upcoming Autoship orders for prenotice email """
    orders = []
    try:
        conn = get_mom_connection()
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


def get_backorders():
    """ Gets backorders for notice email """
    # TODO get_backorders
    pass


def get_new_orders():
    """
    Get new orders from MOM by calling sproc "Emailer_GetNewOrders"
    """
    orders = []
    try:
        conn = get_mom_connection()
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


def get_mom_connection():
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


def setup_sqlite():
    """ Create SQLite3 tracking database if it doesn't exist """
    con = None

    try:
        con = sqlite3.connect('sender.db')
        cur = con.cursor()
        logging.info("Creating table sent_mail if absent...")

        cur.execute(('''CREATE TABLE IF NOT EXISTS sent_mail
            (id integer primary key, email text, mailing text,
            external_id text, sent_at datetime)'''))

        con.commit()
        cur.close()
    except sqlite3.OperationalError, msg:
        logging.error(msg)
        raise
    except sqlite3.DatabaseError, msg:
        logging.error(msg)
        raise
    finally:
        con.close()


def record_sent_mail(email, mailing, external_id=None):
    """
    Writes a record indicating that a mailing has been sent to a
    specific email address. This will ensure avoiding duplication of sent
    emails.
    """
    con = None
    try:
        con = sqlite3.connect('sender.db')
        cur = con.cursor()
        logging.info("Recording email sent to " + email)
        if external_id:
            cur.execute(('''
                INSERT INTO sent_mail (email, mailing, external_id, sent_at)
                VALUES (?, ?, ?, datetime())'''), (email, str(mailing), str(external_id), ))
        else:
            cur.execute(('''
                INSERT INTO sent_mail (email, mailing, external_id, sent_at)
                VALUES (?, ?, NULL, datetime())'''), (email, str(mailing), ))

        logging.info("Inserted %d records. " % cur.rowcount)
        con.commit()
        cur.close()
    except sqlite3.OperationalError, msg:
        logging.error(msg)
        raise
    except sqlite3.DatabaseError, msg:
        logging.error(msg)
        raise
    finally:
        con.close()


def was_mail_sent(email, mailing, external_id=None):
    """
    Determines if a mailing has been sent to a specific email address.
    This will ensure avoiding duplication of sent emails.
    """

    con = None

    try:
        con = sqlite3.connect('sender.db')
        cur = con.cursor()
        logging.info("Looking for email %s sent to %s with id %s" % (mailing, email, external_id))

        if not external_id:
            cur.execute(
                ("SELECT COUNT(email) "
                    "FROM sent_mail "
                    "WHERE email = ? "
                    "AND mailing = ?"), (email, mailing, ))
        else:
            cur.execute(
                ("SELECT COUNT(email) FROM sent_mail WHERE email = ? "
                 "AND mailing = ? "
                 "AND external_id = ?"), (email, mailing, str(external_id), ))

        sent_count = cur.fetchone()[0]
        logging.info("Found %d records." % sent_count)
        con.commit()
        cur.close()
        return sent_count > 0
    except sqlite3.OperationalError, msg:
        logging.error(msg)
        raise
    except sqlite3.DatabaseError, msg:
        logging.error(msg)
        raise
    except sqlite3.Error as error:
        logging.error(error.message)
        raise
    finally:
        con.close()


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
    main()
