#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pinnacle Cart API Client
"""

from ConfigParser import ConfigParser, Error
import logging
import requests
import json
import oursql

API_URL = \
    'https://www.nutri-health.com/content/admin/plugins/openapi/index.php'


class PinnacleClient(object):
    """ Pinnacle API Client Class """
    def __init__(self):
        config = ConfigParser()
        try:
            config.read("config.ini")
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
        config = ConfigParser()
        try:
            config.read("config.ini")
        except Error:
            msg = "config.ini file bad or missing"
            logging.error(msg)
            raise Exception(msg)
        try:
            self.username = config.get("webdb", "username")
            self.password = config.get("webdb", "password")
            self.host = config.get("webdb", "host")
            self.db = config.get("webdb", "db")
        except Error:
            msg = "Config section [webdb] bad or missing"
            logging.error(msg)
            raise Exception(msg)

    def get_abandoned_carts(self):
        """ Get List of Abandoned Carts """
        conn = oursql.connect(host=self.host, user=self.username,
                              passwd=self.password, db=self.db)
        curs = conn.cursor(oursql.DictCursor)
        curs.execute((
            "SELECT users.email, orders.create_date "
            "FROM orders "
            "inner join users on (users.uid = orders.uid) "
            "where orders.status = 'Abandon' "
            "and users.email <> '' "
            "order by create_date desc"))

        while 1:
            row = curs.fetchone()
            if row is None:
                break
            print "%s" % (row['email'])


if __name__ == '__main__':
    pc = PinnacleDBClient()
    carts = pc.get_abandoned_carts()
    print carts
