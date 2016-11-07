#!/usr/bin/python
# -*- coding: utf8 -*-

from google.appengine.ext import db
from datetime import datetime, timedelta
import json
from base_test_case import BaseTestCase
from constants import *
from models import Enterprise, User, Sensor, SensorType, Analysis
from echosense import app as tst_app

TEST_NUM = "254729000000"
TEST_EMAIL = "test@hello.com"
PW = "hello123"
E_ALIAS = "test"

class APITestCase(BaseTestCase):

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

        self.st = SensorType.Create(self.e)
        self.st.Update(alias="geo")
        self.st.put()

    def __commonParams(self):
        return {
            'auth': API_AUTH,
            'uid': self.u.key().id(),
            'pw': PW
        }

    def testPhoneLogin(self):
        params = {
            'auth': API_AUTH,
            '_login': TEST_NUM,
            '_pw': PW
        }
        res = self.post("/api/login", params)
        self.assertOK(res)
        normal_body = json.loads(res.normal_body)
        self.assertTrue(normal_body['success'])

    def __login(self):
        params = {
            'auth': API_AUTH,
            '_login': TEST_EMAIL,
            '_pw': PW
        }
        return self.post("/api/login", params)


    def testEmailLogin(self):
        res = self.__login()
        self.assertOK(res)
        normal_body = json.loads(res.normal_body)
        self.assertTrue(normal_body['success'])

    def testSensorAPIs(self):
        self.sensor1 = Sensor.Create(self.e, "000-100", self.st.key().id())
        self.sensor1.Update(name="Sensor 1")
        self.sensor2 = Sensor.Create(self.e, "000-200", self.st.key().id())
        db.put([self.sensor1, self.sensor2])

        # Test list
        params = self.__commonParams()
        result = self.get_json("/api/sensor", params)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['data']['sensors']), 2)

        # Test detail
        params = self.__commonParams()
        params['with_records'] = 10
        result = self.get_json("/api/sensor/%s" % "000-100", params)
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['sensor']['name'], "Sensor 1")

        # Test create with alias
        params = self.__commonParams()
        KN = "00-200"
        params['kn'] = KN
        params['name'] = "Geo Sensor 1"
        params['sensortype_alias'] = "geo"
        result = self.post_json("/api/sensor", params)
        self.assertTrue(result['success'])
        s = Sensor.get_by_key_name(KN, parent=self.e.key())
        self.assertIsNotNone(s)
        self.assertEqual(s.name, "Geo Sensor 1")
        self.assertEqual(s.sensortype.key(), self.st.key())

    def testAnalysisAPIs(self):
        print ">>>>>>>>>>>>>>>"
        self.analysis = Analysis.Get(self.e, "ROLLUP", get_or_insert=True)
        self.analysis.put()

        # Test update
        params = self.__commonParams()
        params.update({
            'akn': 'ROLLUP',
            'cols': 'TOTAL,MINIMUM',
            'TOTAL': 10,
            'MINIMUM': 2.5
            })
        result = self.post_json("/api/analysis", params)
        print result
        self.assertTrue(result['success'])

        # Test detail
        params = self.__commonParams()
        params['with_props'] = 1
        result = self.get_json("/api/analysis/ROLLUP", params)
        print result
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['analysis']['columns']['TOTAL'], '10')
        self.assertEqual(result['data']['analysis']['columns']['MINIMUM'], '2.5')

    def testEnterpriseLookup(self):
        # self.__login()
        result = self.get_json("/api/public/enterprise_lookup/%s" % E_ALIAS, {"type": "alias"})
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['enterprise']['name'], self.e.name)


    def tearDown(self):
        pass



