#!/usr/bin/python
# -*- coding: utf8 -*-

import unittest
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed

from datetime import datetime, timedelta
import tools
import json
from google.appengine.ext import deferred
import logging
import os
import random
from constants import *
from models import Enterprise, SensorType, Sensor, Record, Rule, Alarm, ProcessTask, SensorProcessTask, Analysis, User, Payment
from base_test_case import BaseTestCase
from echosense import app as tst_app

TEST_SENSOR_ID = "00-100"
ANALYSIS_KEY_PATTERN = '%SID_%Y-%M-%D'
INTERVAL_SECS = 3

class AlarmExpressionsTestCase(BaseTestCase):

    def setUp(self):
        self.set_application(tst_app)
        self.setup_testbed()
        self.init_datastore_stub()
        self.init_memcache_stub()
        self.init_taskqueue_stub()
        self.init_mail_stub()
        self.register_search_api_stub()
        self.init_urlfetch_stub()

        # Create enterprise, sensortype and sensor
        self.e = Enterprise.Create()
        self.e.Update(name="Test Ent", timezone="Africa/Nairobi")
        self.e.put()

        self.tracker = SensorType.Create(self.e)
        schema = {
            'speed': {
                'unit': 'kph'
            },
            'ign_on': {
                'unit': 'boolean'
            },
            'ign_off': {
                'unit': 'boolean'
            }

        }
        self.tracker.Update(name="Tracker Sensor", schema=json.dumps(schema))
        self.tracker.put()

        self.vehicle_1 = Sensor.Create(self.e, TEST_SENSOR_ID, self.tracker.key().id())
        self.vehicle_1.Update(
            sensortype_id=self.tracker.key().id(),
            name="Vehicle Sensor 1"
            )
        self.vehicle_1.put()

        # Create alarm
        self.ign_on_alarm = Rule.Create(self.e)
        self.ign_on_alarm.Update(
            name="Ignition On",
            sensortype_id=self.tracker.key().id(),
            column="ign_on",
            trigger=RULE.CEILING,
            value2=0,
            consecutive_limit=-1,
            duration=0)
        self.ign_on_alarm.put()
        self.ign_off_alarm = Rule.Create(self.e)
        self.ign_off_alarm.Update(
            name="Ignition Off",
            sensortype_id=self.tracker.key().id(),
            column="ign_off",
            trigger=RULE.CEILING,
            value2=0,
            consecutive_limit=-1,
            duration=0,
            spec=json.dumps({'processers': [
                {
                    'analysis_key_pattern': ANALYSIS_KEY_PATTERN,
                    'expr': '. + SINCE(LAST_ALARM(%d)) / 1000' % self.ign_on_alarm.key().id(),
                    'column': 'on_secs'
                }
            ]}))
        self.ign_off_alarm.put()

    def __createNewRecords(self, data, first_dt=None, interval_secs=3, sensor=None):
        if not sensor:
            sensor = self.vehicle_1
        now = first_dt if first_dt else datetime.now()
        records = []
        N = len(data.values()[0])
        for i in range(N):
            _r = {}
            for column, vals in data.items():
                _r[column] = vals[i]
            if 'ts' in data:
                # If ts passed in record, overrides
                now = util.ts_to_dt(data['ts'])
            else:
                now += timedelta(seconds=interval_secs)
            r = Record.Create(tools.unixtime(now), sensor, _r, allow_future=True)
            records.append(r)
        db.put(records)
        sensor.dt_updated = datetime.now()
        sensor.put()
        logging.debug("Created %d records" % len(records))

    def __runProcessing(self):
        self.sp.run()  # Fires background worker
        # Force completion
        self.execute_tasks_until_empty()

    def testSinceAlarmProcessing(self):
        self.process = ProcessTask.Create(self.e)
        self.process.Update(rule_ids=[self.ign_on_alarm.key().id(), self.ign_off_alarm.key().id()])
        self.process.put()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_1)
        self.sp.put()

        BATCH_1 = {
            'speed':   [0,  5,  15, 35, 60, 80, 83, 88, 85, 20, 0,  0,  0,  0,  15, 92, 90, 0,  0],
            'ign_on':  [0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0], # Ignition on twice
            'ign_off': [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  1,  0] # Ignition off twice
        }
        self.__createNewRecords(BATCH_1, first_dt=datetime.now() - timedelta(minutes=5), interval_secs=INTERVAL_SECS)
        self.__runProcessing()

        # Confirm analyzed total on seconds
        a = Analysis.GetOrCreate(self.vehicle_1, ANALYSIS_KEY_PATTERN)
        self.assertIsNotNone(a)
        self.assertEqual(a.columnValue('on_secs'), 13 * INTERVAL_SECS)

        self.sp = SensorProcessTask.Get(self.process, self.vehicle_1)
        self.assertEqual(self.sp.status_last_run, PROCESS.OK)


    def tearDown(self):
        pass



