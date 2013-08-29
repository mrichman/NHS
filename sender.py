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
from ConfigParser import SafeConfigParser, Error
from time import strftime
from pymssql import connect, InterfaceError
from suds.client import Client
import sqlite3


LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

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

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)


def create_request():
    """ Creates EmailVision SOAP Request Client """
    client = Client(
        'http://api.notificationmessaging.com/NMSOAP/NotificationService?wsdl')

    return client.factory.create('sendRequest')


def send_object(request):
    """ Sends SOAP Request """
    client = Client(
        'http://api.notificationmessaging.com/NMSOAP/NotificationService?wsdl')
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
        default='pinnacle_export.log',
        help='logging file. Default is pinnacle_export.log.'
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

    logging_level = LOGGING_LEVELS.get(args.l, logging.NOTSET)
    logging.basicConfig(level=logging_level, filename=args.f,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    logging.info(args.m)

    if args.m == 'order-conf':
        order_ack()
    elif args.m == 'test-email':
        test_email()
    elif args.m == 'ship-conf':
        ship_confirmation()
    elif args.m == 'as-prenotice':
        autoship_prenotice()
    elif args.m == 'cart-abandon-20m':
        cart_abandon()
    elif args.m == 'backorder':
        backorder_notice()


def test_email():
    """ Send test email """
    req = create_request()

    req.dyn = [
        {
            'entry': [{"key": 'TEST', 'value': 'This is a test email'}]
        }
    ]

    req.content = [
        {
            'entry': [
                {'key': 1, 'value': '<table border=\'5\'><tr><td>'},
                {'key': 2, 'value': '</td></tr></table>'}]
        }
    ]

    req.email = 'mark.richman@nutrihealth.com'
    config = SafeConfigParser()
    config.read('config.ini')
    key = config.get("emailvision", "test_key")
    req.encrypt = key
    req.notificationId = TEMPLATES["[EMV] Test"]
    req.random = RANDOMTAGS["[EMV] Test"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    res = send_object(req)
    logging.debug(res)
    record_sent_mail(req.email, req.notificationId, '')


def ship_confirmation():
    """ Ship Confirmation Email """
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    config = SafeConfigParser()
    config.read('config.ini')
    key = config.get("emailvision", "ship_conf_key")
    req.encrypt = key
    req.notificationId = TEMPLATES["Trigger_OrderShipment1"]
    req.random = RANDOMTAGS["Trigger_OrderShipment1"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    res = send_object(req)
    logging.debug(res)


def order_ack():
    """ Order Acknowledgement Email """
    get_new_orders()
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    config = SafeConfigParser()
    config.read('config.ini')
    key = config.get("emailvision", "order_conf_key")
    req.encrypt = key
    req.notificationId = TEMPLATES["Trigger_OrderAckknowledge1"]
    req.random = RANDOMTAGS["Trigger_OrderAckknowledge1"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    res = send_object(req)
    logging.debug(res)


def cart_abandon():
    """ Cart Abandonment Email """
    config = SafeConfigParser()
    config.read('config.ini')
    key = config.get("emailvision", "cart_abandon_key")
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    req.encrypt = key
    req.notificationId = TEMPLATES["TEST-Drift-Trigger1"]
    req.random = RANDOMTAGS["TEST-Drift-Trigger1"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    res = send_object(req)
    logging.debug(res)


def autoship_prenotice():
    """ Autoship Prenotice Email """
    orders = get_upcoming_autoship_orders()
    config = SafeConfigParser()
    config.read('config.ini')
    key = config.get("emailvision", "as_prenotice_key")
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    req.encrypt = key
    req.notificationId = TEMPLATES["Autoship-Prenotice"]
    req.random = RANDOMTAGS["Autoship-Prenotice"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    res = send_object(req)
    logging.debug(res)
    record_sent_mail(req.email, req.notificationId, '')


def backorder_notice():
    """ Backorder Notice Email """
    orders = get_backorders()
    config = SafeConfigParser()
    config.read('config.ini')
    key = config.get("emailvision", "backorder_notice_key")
    req = create_request()
    req.email = 'mark.richman@nutrihealth.com'
    req.encrypt = key
    req.notificationId = TEMPLATES["Backorder-Notice"]
    req.random = RANDOMTAGS["Backorder-Notice"]
    req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
    req.synchrotype = 'NOTHING'
    req.uidkey = 'email'
    res = send_object(req)
    logging.debug(res)
    record_sent_mail(req.email, req.notificationId, '')


def get_upcoming_autoship_orders():
    """ Gets upcoming Autoship orders for prenotice email """
    #TODO
    pass


def get_backorders():
    """ Gets backorders for notice email """
    #TODO
    pass


def get_new_orders():
    """
    Get new orders from MOM by calling sproc "Emailer_GetNewOrders"
    """

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
        logging.info('Getting new orders')
        conn = connect(host=momdb_host, user=momdb_user,
                       password=momdb_password,
                       database=momdb_db, as_dict=True)
        cur = conn.cursor()
        cur.callproc("Emailer_GetNewOrders")
        for row in cur:
            logging.debug("CUSTNUM=%d, FIRSTNAME=%s" % (
                row['CUSTNUM'], row['FIRSTNAME']))
        conn.close()
    except InterfaceError as error:
        msg = "Error connecting to SQL Server: %s" % error.message
        logging.error(msg)
        exit(msg)


def record_sent_mail(email, mailing, external_id):
    """
    Writes a record indicating that a mailing has been sent to a
    specific email address. This will ensure avoiding duplication of sent
    emails.
    """

    con = None

    try:
        con = sqlite3.connect('sender.db')

        cur = con.cursor()

        logging.info("Creating table sent_mail")

        cur.execute(('''CREATE TABLE IF NOT EXISTS sent_mail
            (id integer primary key, email text, mailing text,
            external_id text, sent_at datetime)'''))

        logging.info("Recording email sent to " + email)

        cur.execute(('''
            INSERT INTO sent_mail (email, mailing, external_id, sent_at)
            VALUES (?, ?, ?, datetime())'''), (email, mailing, external_id, ))

        logging.info("Rows affected: " + str(cur.rowcount))

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


if __name__ == '__main__':
    main()
