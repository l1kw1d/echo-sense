#!/usr/bin/python
# -*- coding: utf8 -*-

from datetime import datetime
import json
from base_test_case import BaseTestCase
from constants import *
from models import Enterprise, User
from echosense import app as tst_app

TEST_NUM = "254729000000"
TEST_EMAIL = "test@hello.com"
PW = "hello123"
E_ALIAS = "test"

class PublicAPITestCase(BaseTestCase):

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

    def __commonParams(self):
        return {
            'auth': API_AUTH,
            'uid': self.u.key().id(),
            'pw': PW
        }

    def __login(self):
        params = {
            'auth': API_AUTH,
            '_login': TEST_EMAIL,
            '_pw': PW
        }
        return self.post("/api/login", params)


    def testForgotPassword(self):
        res = self.post_json("/api/public/forgot_password/%s" % TEST_NUM, {})
        self.assertEqual(res.get('message'), "A new password is being sent via SMS")


    def tearDown(self):
        pass



