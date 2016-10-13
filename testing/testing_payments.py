#!/usr/bin/python
# -*- coding: utf8 -*-

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed
from expressionParser import ExpressionParser
from datetime import datetime, timedelta
import json
from google.appengine.ext import deferred
from base_test_case import BaseTestCase
from constants import *
from models import Enterprise, User, Sensor, SensorType, Payment
from echosense import app as tst_app

TEST_NUM = "254729000000"
TEST_EMAIL = "test@hello.com"
PW = "hello123"
E_ALIAS = "test"

class PaymentTestCase(BaseTestCase):

    def setUp(self):
        self.set_application(tst_app)
        self.setup_testbed()
        self.init_datastore_stub()
        self.init_memcache_stub()
        self.init_taskqueue_stub()
        self.register_search_api_stub()
        self.init_modules_stub()

        # Create enterprise, sensortype and sensor
        self.e = Enterprise.Create()
        self.e.Update(name="Test Ent", alias=E_ALIAS.upper())
        self.e.put()

        self.u = User.Create(self.e, phone=TEST_NUM, email=TEST_EMAIL)
        self.u.Update(password=PW, level=USER.ACCOUNT_ADMIN)
        self.u.put()

    def testPaymentCallback(self):

        pmnt = Payment.Request(self.e, self.u, 40)
        self.assertFalse(pmnt.can_send()) # Already sent
        self.assertEqual(pmnt.attempts, 1)
        self.assertEqual(pmnt.status, PAYMENT.SENT)

        # Receive spoof callback - Failure
        data = {
            'requestId': pmnt.gateway_id,
            'status': 'Failed'
        }
        res = self.post("/gateway/payments/atalking", data)
        self.assertOK(res)
        self.assertEqual(res.normal_body, "Callback Accepted")

        # Reload from db
        pmnt = Payment.get(pmnt.key())
        self.assertTrue(pmnt.status, PAYMENT.FAILED)

        # Receive spoof callback - Success
        data = {
            'requestId': pmnt.gateway_id,
            'status': 'Success'
        }
        res = self.post("/gateway/payments/atalking", data)
        self.assertOK(res)
        self.assertEqual(res.normal_body, "Callback Accepted")

        # Reload from db
        pmnt = Payment.get(pmnt.key())
        self.assertTrue(pmnt.status, PAYMENT.CONFIRMED)



    def tearDown(self):
        pass



