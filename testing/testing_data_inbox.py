#!/usr/bin/python
# -*- coding: utf8 -*-

import unittest
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed

from datetime import datetime, timedelta
import tools
import json
import math
from google.appengine.ext import deferred
import logging
import os
import random
from models import Enterprise, SensorType, Sensor, Record
from base_test_case import BaseTestCase
from echosense import app as tst_app
from constants import *

TEST_SENSOR_ID = "ABC"

class DataInboxTestCase(BaseTestCase):

    def setUp(self):
        self.set_application(tst_app)
        self.setup_testbed()
        self.init_datastore_stub()
        self.init_memcache_stub()
        self.init_taskqueue_stub()
        self.register_search_api_stub()

        # Create enterprise, sensortype and sensor
        self.e = Enterprise.Create()
        self.e.Update(name="Test Ent")
        self.e.put()

        self.geosensor = SensorType.Create(self.e)
        schema = {
            'location': {
                'unit': 'deg',
                'label': "Location",
                'role': [COLUMN.LOCATION]
            },
            'ax': {},
            'ay': { 'unit': 'm/s^2', 'type': 'number' },
            'az': { 'unit': 'm/s^2', 'type': 'number' },
            'accel_mag': {
                'unit': 'm/2^2',
                'label': "Acceleration Magnitude",
                'calculation': "SQRT([ax]^2 + [ay]^2 + [az]^2)"
            }
        }
        self.geosensor.Update(name="Geo Sensor", schema=json.dumps(schema))
        self.geosensor.put()

        self.geosensor1 = Sensor.Create(self.e, TEST_SENSOR_ID, self.geosensor.key().id())
        self.geosensor1.Update(sensortype_id=self.geosensor.key().id(), name="Geo Sensor 1")
        self.geosensor1.put()


    def testGeoJsonIn(self):
        uri = "/%s/inbox/json/%s" % (self.e.key().id(), TEST_SENSOR_ID)
        lat = 1.3
        lon = 36.9
        MOVE_SIZE = 0.01
        MAX_ACCEL = 10
        N_POINTS = 10
        DELAY_SECS = 1
        now = datetime.now() - timedelta(seconds=60)

        # Populate dummy data with random moves
        data = []
        target_accel_mags = []
        for x in range(N_POINTS):
            now += timedelta(seconds=DELAY_SECS)
            lat += (random.random()-0.5) * MOVE_SIZE
            lon += (random.random()-0.5) * MOVE_SIZE
            loc = "%s,%s" % (lat, lon)
            ax = (random.random() * MAX_ACCEL) - MAX_ACCEL/2
            ay = (random.random() * MAX_ACCEL) - MAX_ACCEL/2
            az = (random.random() * MAX_ACCEL) - MAX_ACCEL/2
            accel_mag = math.sqrt(pow(ax,2)+pow(ay,2)+pow(az,2))
            target_accel_mags.append(accel_mag)
            data.append({
                'timestamp': tools.unixtime(dt=now),  # milliseconds
                'location': loc,
                'ax': ax,
                'ay': ay,
                'az': az
            })
        last_loc = loc
        body = json.dumps(data)
        response = self.post(uri, body)
        self.assertEqual(response.status_int, 200)
        content = json.loads(response.normal_body)
        self.assertTrue(content['success'])
        self.assertEqual(content['data']['count'], N_POINTS)

        # Fetch created records from db
        records = Record.Fetch(self.geosensor1)
        self.assertEqual(len(records), N_POINTS)
        last_r = records[0]
        self.assertEqual(tools.unixtime(last_r.dt_recorded), tools.unixtime(now))

        accel_mags = [r.columnValue('accel_mag') for r in records]
        self.assertListEqual(accel_mags, list(reversed(target_accel_mags)))

        # Confirm sensor state update
        self.geosensor1 = Sensor.get(self.geosensor1.key())  # Refetch from db
        self.assertEqual(self.geosensor1.location, db.GeoPt(last_loc))

    def testFutureRecords(self):
        uri = "/%s/inbox/json/%s" % (self.e.key().id(), TEST_SENSOR_ID)
        lat = 1.3
        lon = 36.9
        MOVE_SIZE = 0.01
        N_POINTS = 10
        DELAY_SECS = 1
        now = datetime.now()

        # Populate dummy data with random moves
        data = []
        for x in range(N_POINTS):
            now += timedelta(seconds=DELAY_SECS)
            lat += (random.random()-0.5) * MOVE_SIZE
            lon += (random.random()-0.5) * MOVE_SIZE
            loc = "%s,%s" % (lat, lon)
            data.append({
                'timestamp': tools.unixtime(dt=now) + 1000*60,  # ms (1 minute in future)
                'location': loc
            })
        last_loc = loc
        body = json.dumps(data)
        response = self.post(uri, body)
        self.assertEqual(response.status_int, 200)
        content = json.loads(response.normal_body)
        self.assertTrue(content['success'])
        self.assertEqual(content['data']['count'], N_POINTS)

        # Fetch created records from db
        records = Record.Fetch(self.geosensor1)
        # Allowing future creation in buffer, so we should have all 10 records
        self.assertEqual(len(records), 10)

    def testNonSaneFutureRecords(self):
        uri = "/%s/inbox/json/%s" % (self.e.key().id(), TEST_SENSOR_ID)
        lat = 1.3
        lon = 36.9
        MOVE_SIZE = 0.01
        N_POINTS = 10
        DELAY_SECS = 1
        now = datetime.now()

        # Populate dummy data with random moves
        data = []
        for x in range(N_POINTS):
            now += timedelta(seconds=DELAY_SECS)
            lat += (random.random()-0.5) * MOVE_SIZE
            lon += (random.random()-0.5) * MOVE_SIZE
            loc = "%s,%s" % (lat, lon)
            data.append({
                'timestamp': tools.unixtime(dt=now) + 1000*60*60*24*30,  # Non-sane (1 month in future)
                'location': loc
            })
        last_loc = loc
        body = json.dumps(data)
        response = self.post(uri, body)
        self.assertEqual(response.status_int, 200)
        content = json.loads(response.normal_body)
        self.assertTrue(content['success'])
        self.assertEqual(content['data']['count'], N_POINTS)

        # Fetch created records from db
        records = Record.Fetch(self.geosensor1)
        self.assertEqual(len(records), 0) # No records saved, all non-sane


    def testStateUpdates(self):
        self.geosensor1 = Sensor.get(self.geosensor1.key())  # Refetch from db
        self.geosensor1.update_state(COLUMN.LOCATION, NBO_LOC)
        self.assertEqual(self.geosensor1.location, db.GeoPt(NBO_LOC))

    def tearDown(self):
        pass



