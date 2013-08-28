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
from ConfigParser import SafeConfigParser, Error
from time import strftime
import logging
from pymssql import connect, InterfaceError
from suds.client import Client


LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

TEMPLATES = {"[EMV] Test": 15367,
             "Trigger_OrderShipment1": 1532948,
             "Trigger_OrderAckknowledge1": 1532947,
             "TEST-Drift-Trigger1": 1531070}

RANDOMTAGS = {"[EMV] Test": 'FA6100040001FF8C',
              "Trigger_OrderShipment1": '952110747E020009',
              "Trigger_OrderAckknowledge1": '9D1F8080000474AA',
              "TEST-Drift-Trigger1": '608D795E7C020060'}

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

    #TODO respect command line args for each email
    test_email()
    order_ack()
    test_drift_trigger1()
    ship_confirmation()
    get_new_orders()


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
    print(res)


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
    print(res)


def order_ack():
    """ Order Acknowledgement Email """
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

    print(res)


def test_drift_trigger1():
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

    print(res)


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
        print 'Getting new orders...'
        conn = connect(host=momdb_host, user=momdb_user,
                       password=momdb_password,
                       database=momdb_db, as_dict=True)
        cur = conn.cursor()
        cur.callproc("Emailer_GetNewOrders")
        for row in cur:
            print "CUSTNUM=%d, FIRSTNAME=%s" % (
                row['CUSTNUM'], row['FIRSTNAME'])
        conn.close()
    except InterfaceError as error:
        msg = "Error connecting to SQL Server: %s" % error.message
        logging.error(msg)
        exit(msg)


if __name__ == '__main__':
    main()
