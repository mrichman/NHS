#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EmailVision Client
"""

import logging
from time import strftime
from suds.client import Client

WSDL_URL = \
    'http://api.notificationmessaging.com/NMSOAP/NotificationService?wsdl'

TEMPLATES = {"[EMV] Test": 15367,
             "Trigger_OrderShipment1": 1532948,
             "Trigger_OrderAckknowledge1": 1532947,
             "TEST-Drift-Trigger1": 1531070,
             "Autoship-Prenotice": 1536856,
             "Backorder-Notice": 1536855}

RANDOM_TAGS = {"[EMV] Test": 'FA6100040001FF8C',
              "Trigger_OrderShipment1": '952110747E020009',
              "Trigger_OrderAckknowledge1": '9D1F8080000474AA',
              "TEST-Drift-Trigger1": '608D795E7C020060',
              "Autoship-Prenotice": '76FC140010000D9E',
              "Backorder-Notice": '1E78EC9828002001'}


class EmailVisionClient(object):
    """ EmailVision SOAP Client """
    def __init__(self):
        pass

    def create_request(self, mailing_name):
        """ Creates EmailVision SOAP Request Client """
        client = Client(WSDL_URL)
        req = client.factory.create('sendRequest')
        req.notificationId = TEMPLATES[mailing_name]
        req.random = RANDOM_TAGS[mailing_name]
        req.senddate = strftime("%Y-%m-%dT%H:%M:%S")  # '1980-01-01T00:00:00'
        req.synchrotype = 'NOTHING'
        req.uidkey = 'email'
        return req

    def send_object(self, request):
        """ Sends SOAP Request """
        logging.info("Sending SOAP request...")
        client = Client(WSDL_URL)
        return client.service.sendObject(request)
