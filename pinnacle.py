#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pinnacle Cart API Client
"""

from ConfigParser import ConfigParser, Error
import logging
import requests
import json

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
            exit(msg)
        try:
            self.pcapi_username = config.get("pcapi", "username")
            self.pcapi_password = config.get("pcapi", "password")
            self.pcapi_token = config.get("pcapi", "password")
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
            'call': 'GetProducts',
            'PrimaryCategory': -1}

        req = requests.get(API_URL, params=payload)

        # print r.status_code
        # print r.text
        data = json.loads(req.text, encoding='ascii')
        return data

if __name__ == '__main__':
    pc = PinnacleClient()
    carts = pc.get_abandoned_carts()
    print carts
