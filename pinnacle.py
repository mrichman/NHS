#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pinnacle Cart API Client
"""

from ConfigParser import SafeConfigParser, Error
import logging
import requests
import json
import oursql
import os

API_URL = \
    'https://www.nutri-health.com/content/admin/plugins/openapi/index.php'


class PinnacleClient(object):
    """ Pinnacle API Client Class """
    def __init__(self):
        config = SafeConfigParser()
        try:
            config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        except Error:
            msg = "config.ini file bad or missing"
            logging.error(msg)
            raise Exception(msg)
        try:
            self.pcapi_username = config.get("pcapi", "username")
            self.pcapi_password = config.get("pcapi", "password")
            self.pcapi_token = config.get("pcapi", "token")
        except Error:
            msg = "Config section [pcapi] bad or missing"
            logging.error(msg)
            raise Exception(msg)

    def get_abandoned_carts(self):
        """ Get List of Abandoned Carts """
        payload = {
            'username': self.pcapi_username,
            'password': self.pcapi_password,
            'token': self.pcapi_token,
            'apiType': 'json',
            'call': 'GetOrders',
            'Status': 'Abandon'}

        res = requests.get(API_URL, params=payload)

        # print r.status_code
        # print r.text
        data = json.loads(res.text, encoding='ascii')
        return data


class PinnacleDBClient(object):
    """ Pinnacle DB Client Class """
    def __init__(self):
        config = SafeConfigParser()
        try:
            config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        except Error:
            msg = "config.ini file bad or missing"
            logging.error(msg)
            raise Exception(msg)
        try:
            self.username = config.get("webdb", "user")
            self.password = config.get("webdb", "password")
            self.host = config.get("webdb", "host")
            self.db = config.get("webdb", "db")
        except Error:
            msg = "Config section [webdb] bad or missing"
            logging.error(msg)
            raise Exception(msg)

    def get_abandoned_carts(self, minutes):
        """ Get List of Abandoned Carts """
        logging.info("Getting abandoned carts %d minutes old." % minutes)
        conn = oursql.connect(host=self.host, user=self.username,
                              passwd=self.password, db=self.db)
        curs = conn.cursor(oursql.DictCursor)
        sql = (
            "SELECT users.email, users.fname "
            "FROM orders "
            "inner join users on (users.uid = orders.uid) "
            "where orders.status = 'Abandon' "
            "and users.email <> '' "
            "and create_date < (NOW() - INTERVAL " + str(minutes) + " MINUTE) "
            "order by create_date desc")
        logging.debug(sql)
        curs.execute(sql)

        carts = []

        rows = curs.fetchall()
        for row in rows:
            cart = (row['email'], row['fname'])
            logging.debug(cart)
            carts.append(cart)

        logging.info("Found %d abandoned carts." % len(carts))
        return carts


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)
    # console handler with specified log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(console_handler)
    pc = PinnacleDBClient()
    # carts = pc.get_abandoned_carts(24 * 60)  # 24h
    carts = pc.get_abandoned_carts(20)
    print carts
