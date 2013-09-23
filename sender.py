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

from argparse import ArgumentParser
from ConfigParser import SafeConfigParser
import logging
import logging.handlers
import os
from sqlite3 import DatabaseError, OperationalError, connect, Error
from emailvision import EmailVisionClient
from mom import MOMClient, Order
from pinnacle import PinnacleDBClient
from wordpress import WordPressDBClient


LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

MAILINGS = ['order-conf', 'ship-conf', 'as-prenotice', 'backorder', 'blog-sub',
            'blog-unsub', 'cust-survey', 'cart-abandon-20min',
            'cart-abandon-24h', 'test-email']


def main():
    """ Main function """
    parser = ArgumentParser(description="EmailVision Sender")
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

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging_level)
    logging.getLogger().addHandler(console_handler)

    smtp_handler = BufferingSMTPHandler(
        mailhost='localhost',
        fromaddr='noreply@nutrihealth.com',
        toaddrs=['mark.richman@nutrihealth.com'],
        subject='[EmailVision] sender.py log',
        capacity=1000)
    # smtp_handler.mailport = 1025
    smtp_handler.setLevel(logging_level)
    logging.getLogger().addHandler(smtp_handler)

    setup_sqlite()

    logging.info(args.m)

    if args.m == 'order-conf':
        order_conf()
    elif args.m == 'test-email':
        test_email()
    elif args.m == 'ship-conf':
        ship_confirmation()
    elif args.m == 'as-prenotice':
        autoship_prenotice()
    elif args.m == 'cart-abandon-20min':
        cart_abandon_20m()
    elif args.m == 'cart-abandon-24h':
        cart_abandon_24h()
    elif args.m == 'backorder':
        backorder_notice()
    elif args.m == 'blog-sub':
        blog_sub()
    elif args.m == 'blog-unsub':
        blog_unsub()


def test_email():
    """ Send test email """
    order = Order()
    order.first_name = 'John'
    order.last_name = 'Doe'
    order.email = 'john.doe@example.com'
    order.sku = '10400'
    order.description = 'Flora Source 60 ct'
    order.cust_num = 5173525
    order.list_price = 33.00
    order.order_num = 838513
    order.qty = 3
    order.total = 99.00
    order.tax = 0.00
    order.subtotal = 99.00
    order.billing_address1 = '123 Main St.'
    order.billing_address2 = 'Suite 100'
    order.billing_city = 'Anytown'
    order.billing_state = 'XY'
    order.billing_zip = '54321'
    order.expect_ship = '9/12/2013'
    order.payment_last4 = '9876'
    order.payment_type = 'Visa'
    order.promocode_discount = 0.00
    order.ship_type = 'USPS'
    order.shipping_address1 = '123 Main St.'
    order.shipping_address2 = 'Suite 100'
    order.shipping_city = 'Anytown'
    order.shipping_state = 'XY'
    order.shipping_zip = '54321'
    order.source_key = 'THANKS20'
    req = EmailVisionClient().create_request("Trigger_OrderAckknowledge1")
    req.dyn = [
        {
            'entry': [
                {"key": "billing_address1",
                 "value": order.billing_address1},
                {"key": "billing_address2",
                 "value": order.billing_address2},
                {"key": "billing_city", "value": order.billing_city},
                {"key": "billing_state", "value": order.billing_state},
                {"key": "billing_zip", "value": order.billing_zip},
                {"key": "discount", "value": order.discount},
                {"key": "firstname", "value": order.first_name},
                {"key": "last4", "value": order.payment_last4},
                {"key": "lastname", "value": order.last_name},
                {"key": "ordernum", "value": order.order_num},
                {"key": "payment", "value": order.payment_type},
                {"key": "promocode_discount",
                 "value": order.promocode_discount},
                {"key": "shipping_address1",
                 "value": order.shipping_address1},
                {"key": "shipping_address2",
                 "value": order.shipping_address2},
                {"key": "shipping_city", "value": order.shipping_city},
                {"key": "shipping_fee", "value": order.shipping_fee},
                {"key": "shipping_state", "value": order.shipping_state},
                {"key": "shipping_zip", "value": order.shipping_zip},
                {"key": "sourcekey", "value": order.source_key},
                {"key": "subtotal_amt", "value": order.subtotal},
                {"key": "tax_amount", "value": order.tax},
                {"key": "total", "value": order.total}
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
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    req.encrypt = config.get("emailvision", "order_conf_key")
    if not was_mail_sent(req.email, req.notificationId):
        res = EmailVisionClient().send(req)
        logging.debug(res)
        record_sent_mail(req.email, req.notificationId)
    else:
        logging.info("Mail already sent. Skipping.")


def ship_confirmation():
    """ Ship Confirmation Email """
    orders = MOMClient().get_shipped_orders()
    logging.info("Got %d shipped orders from MOM." % len(orders))
    for order in orders:
        req = EmailVisionClient().create_request("Trigger_OrderShipment1")
        req.dyn = [
            {
                'entry': [
                    {"key": "firstname", "value": order.first_name},
                    {"key": "tracking_num", "value": order.tracking_num}
                ]
            }
        ]
        req.email = order.email
        config = SafeConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        req.encrypt = config.get("emailvision", "ship_conf_key")
        if not was_mail_sent(req.email, req.notificationId):
            res = EmailVisionClient().send(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId)
        else:
            logging.debug("Mail already sent. Skipping.")


def order_conf():
    """ Order Confirmation Email """
    orders = MOMClient().get_new_orders()
    logging.info("Got %d orders from MOM." % len(orders))
    for order in orders:
        req = EmailVisionClient().create_request("Trigger_OrderAckknowledge1")
        req.dyn = [
            {
                'entry': [
                    {"key": "billing_address1",
                     "value": order.billing_address1},
                    {"key": "billing_address2",
                     "value": order.billing_address2},
                    {"key": "billing_city", "value": order.billing_city},
                    {"key": "billing_state", "value": order.billing_state},
                    {"key": "billing_zip", "value": order.billing_zip},
                    {"key": "discount",
                     "value": "{0:.2f}".format(order.discount)},
                    {"key": "firstname", "value": order.first_name},
                    {"key": "last4", "value": order.payment_last4},
                    {"key": "lastname", "value": order.last_name},
                    {"key": "ordernum", "value": order.order_num},
                    {"key": "payment", "value": order.payment_type},
                    {"key": "promocode", "value": order.promocode},
                    {"key": "promocode_discount",
                     "value": "{0:.2f}".format(order.promocode_discount)},
                    {"key": "shipping_address1",
                     "value": order.shipping_address1},
                    {"key": "shipping_address2",
                     "value": order.shipping_address2},
                    {"key": "shipping_city", "value": order.shipping_city},
                    {"key": "shipping_fee", "value": order.shipping_fee},
                    {"key": "shipping_state", "value": order.shipping_state},
                    {"key": "shipping_zip", "value": order.shipping_zip},
                    {"key": "sourcekey", "value": order.source_key},
                    {"key": "subtotal_amt",
                     "value": "{0:.2f}".format(order.subtotal)},
                    {"key": "tax_amount", "value": order.tax},
                    {"key": "total", "value": order.total}
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
        req.email = order.email
        config = SafeConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        req.encrypt = config.get("emailvision", "order_conf_key")
        if not was_mail_sent(req.email, req.notificationId, order.order_num):
            res = EmailVisionClient().send(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId, order.order_num)
        else:
            logging.debug("Mail already sent. Skipping.")


def cart_abandon_20m():
    """ Cart Abandonment Email """
    client = PinnacleDBClient()
    carts = client.get_abandoned_carts(20)
    config = SafeConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    for cart in carts:
        req = EmailVisionClient().create_request("CartAbandoned_Drift-20min")
        req.email = cart[0]
        req.dyn = [
            {
                'entry': [
                    {"key": "firstname", "value": cart[1]}
                ]
            }
        ]
        req.encrypt = config.get("emailvision", "cart_abandon_20min_key")
        if not was_mail_sent(req.email, req.notificationId):
            res = EmailVisionClient().send(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId)
        else:
            logging.debug("Mail already sent. Skipping.")


def cart_abandon_24h():
    """ Cart Abandonment Email """
    client = PinnacleDBClient()
    carts = client.get_abandoned_carts(24 * 20)
    config = SafeConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    for cart in carts:
        req = EmailVisionClient().create_request("CartAbandoned_Drift-24h")
        req.email = cart[0]
        req.dyn = [
            {
                'entry': [
                    {"key": "firstname", "value": cart[1]}
                ]
            }
        ]
        req.encrypt = config.get("emailvision", "cart_abandon_24h_key")
        if not was_mail_sent(req.email, req.notificationId):
            res = EmailVisionClient().send(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId)
        else:
            logging.debug("Mail already sent. Skipping.")


def autoship_prenotice():
    """ Autoship Prenotice Email """
    orders = MOMClient().get_upcoming_autoship_orders()
    logging.info("Got %d orders from MOM." % len(orders))
    for order in orders:
        req = EmailVisionClient().create_request("Autoship-Prenotice")
        req.dyn = [
            {
                'entry': [
                    {"key": "billing_address1",
                     "value": order.billing_address1},
                    {"key": "billing_address2",
                     "value": order.billing_address2},
                    {"key": "billing_city", "value": order.billing_city},
                    {"key": "billing_state", "value": order.billing_state},
                    {"key": "billing_zip", "value": order.billing_zip},
                    {"key": "discount", "value": order.discount},
                    {"key": "firstname", "value": order.first_name},
                    {"key": "last4", "value": order.payment_last4},
                    {"key": "lastname", "value": order.last_name},
                    {"key": "ordernum", "value": order.order_num},
                    {"key": "payment", "value": order.payment_type},
                    {"key": "promocode_discount",
                     "value": order.promocode_discount},
                    {"key": "shipdate",
                     "value": order.expect_ship.strftime('%m/%d/%Y')},
                    {"key": "shipping_address1",
                     "value": order.shipping_address1},
                    {"key": "shipping_address2",
                     "value": order.shipping_address2},
                    {"key": "shipping_city", "value": order.shipping_city},
                    {"key": "shipping_fee", "value": order.shipping_fee},
                    {"key": "shipping_state", "value": order.shipping_state},
                    {"key": "shipping_zip", "value": order.shipping_zip},
                    {"key": "sourcekey", "value": order.source_key},
                    {"key": "subtotal_amt", "value": order.subtotal},
                    {"key": "tax_amount", "value": order.tax},
                    {"key": "total", "value": order.total}
                ]
            }
        ]
        req.content = [
            {
                'entry': [
                    {'key': 1, 'value': order.html_table_autoship()}
                ]
            }
        ]
        req.email = order.email
        config = SafeConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        req.encrypt = config.get("emailvision", "as_prenotice_key")
        if not was_mail_sent(req.email, req.notificationId, order.order_num):
            res = EmailVisionClient().send(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId, order.order_num)
        else:
            logging.debug("Mail already sent. Skipping.")


def backorder_notice():
    """ Backorder Notice Email """
    orders = MOMClient().get_backorders()
    logging.info("Got %d backorders from MOM." % len(orders))
    for order in orders:
        req = EmailVisionClient().create_request("Backorder-Notice")
        req.dyn = [
            {
                'entry': [
                    {"key": "billing_address1",
                     "value": order.billing_address1},
                    {"key": "billing_address2",
                     "value": order.billing_address2},
                    {"key": "billing_city", "value": order.billing_city},
                    {"key": "billing_state", "value": order.billing_state},
                    {"key": "billing_zip", "value": order.billing_zip},
                    {"key": "discount", "value": order.discount},
                    {"key": "firstname", "value": order.first_name},
                    {"key": "last4", "value": order.payment_last4},
                    {"key": "lastname", "value": order.last_name},
                    {"key": "ordernum", "value": order.order_num},
                    {"key": "payment", "value": order.payment_type},
                    {"key": "promocode_discount",
                     "value": order.promocode_discount},
                    {"key": "shipping_address1",
                     "value": order.shipping_address1},
                    {"key": "shipping_address2",
                     "value": order.shipping_address2},
                    {"key": "shipping_city", "value": order.shipping_city},
                    {"key": "shipping_fee", "value": order.shipping_fee},
                    {"key": "shipping_state", "value": order.shipping_state},
                    {"key": "shipping_zip", "value": order.shipping_zip},
                    {"key": "sourcekey", "value": order.source_key},
                    {"key": "subtotal_amt", "value": order.subtotal},
                    {"key": "tax_amount", "value": order.tax},
                    {"key": "total", "value": order.total}
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
        req.email = order.email
        config = SafeConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        req.encrypt = config.get("emailvision", "backorder_notice_key")
        if not was_mail_sent(req.email, req.notificationId):
            res = EmailVisionClient().send(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId)
        else:
            logging.debug("Mail already sent. Skipping.")


def blog_sub():
    """ Blog Subscription Email """
    client = WordPressDBClient()
    subs = client.get_blog_subscribers()
    config = SafeConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    for sub in subs:
        req = EmailVisionClient().create_request("Blog-Sub")
        req.email = sub[0]
        req.dyn = [
            {
                'entry': [
                    {"key": "firstname", "value": sub[1]}
                ]
            }
        ]
        req.encrypt = config.get("emailvision", "blog_sub_key")
        if not was_mail_sent(req.email, req.notificationId):
            res = EmailVisionClient().send(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId)
        else:
            logging.debug("Mail already sent. Skipping.")


def blog_unsub():
    """ Blog Unsubscription Email """
    client = WordPressDBClient()
    subs = client.get_blog_unsubscribers()
    config = SafeConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    for sub in subs:
        req = EmailVisionClient().create_request("Blog-Unsub")
        req.email = sub[0]
        req.dyn = [
            {
                'entry': [
                    {"key": "firstname", "value": sub[1]}
                ]
            }
        ]
        req.encrypt = config.get("emailvision", "blog_unsub_key")
        if not was_mail_sent(req.email, req.notificationId):
            res = EmailVisionClient().send(req)
            logging.debug(res)
            record_sent_mail(req.email, req.notificationId)
        else:
            logging.debug("Mail already sent. Skipping.")


def setup_sqlite():
    """ Create SQLite3 tracking database if it doesn't exist """
    con = None

    try:
        con = connect(os.path.join(os.path.dirname(__file__), 'sender.db'))
        cur = con.cursor()
        logging.info("Creating table sent_mail if absent...")

        cur.execute(('''CREATE TABLE IF NOT EXISTS sent_mail
            (id integer primary key, email text, mailing text,
            external_id text, sent_at datetime)'''))

        con.commit()
        cur.close()
    except OperationalError, msg:
        logging.error(msg)
        raise
    except DatabaseError, msg:
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
        con = connect(os.path.join(os.path.dirname(__file__), 'sender.db'))
        cur = con.cursor()
        logging.info("Recording email sent to " + email)
        if external_id:
            cur.execute(('''
                INSERT INTO sent_mail (email, mailing, external_id, sent_at)
                VALUES (?, ?, ?, datetime())'''),
                        (email, str(mailing), str(external_id), ))
        else:
            cur.execute(('''
                INSERT INTO sent_mail (email, mailing, external_id, sent_at)
                VALUES (?, ?, NULL, datetime())'''), (email, str(mailing), ))

        logging.info("Inserted %d records. " % cur.rowcount)
        con.commit()
        cur.close()
    except OperationalError, msg:
        logging.error(msg)
        raise
    except DatabaseError, msg:
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
        con = connect(os.path.join(os.path.dirname(__file__), 'sender.db'))
        cur = con.cursor()
        logging.info("Looking for email %s sent to %s with id %s" %
                     (mailing, email, external_id))

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
    except OperationalError, msg:
        logging.error(msg)
        raise
    except DatabaseError, msg:
        logging.error(msg)
        raise
    except Error as error:
        logging.error(error.message)
        raise
    finally:
        con.close()


class BufferingSMTPHandler(logging.handlers.BufferingHandler):
    """ Buffering SMTP Logging Handler """
    def __init__(self, mailhost, fromaddr, toaddrs, subject, capacity):
        logging.handlers.BufferingHandler.__init__(self, capacity)
        self.mailhost = mailhost
        self.mailport = None
        self.fromaddr = fromaddr
        self.toaddrs = toaddrs
        self.subject = subject
        self.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-5s %(message)s"))

    def flush(self):
        if len(self.buffer) > 0:
            try:
                import smtplib
                import string
                port = self.mailport
                if not port:
                    port = smtplib.SMTP_PORT
                smtp = smtplib.SMTP(self.mailhost, port)
                msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % \
                      (self.fromaddr, string.join(self.toaddrs, ","),
                       self.subject)
                for record in self.buffer:
                    s = self.format(record)
                    print s
                    msg = msg + s + "\r\n"
                smtp.sendmail(self.fromaddr, self.toaddrs, msg)
                smtp.quit()
            except:
                self.handleError(None)  # no particular record
            self.buffer = []


if __name__ == '__main__':
    main()
