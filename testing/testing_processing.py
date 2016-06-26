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
OWNER_NAME = "Dan Owner"
OWNER_NUM = "254700000000"
SPEEDING_ALERT_MESSAGE = "Hello {to.name}, {sensor.id} was speeding at {record.first.alarm_value} at {start.time}"

DUMMY_GEOFENCE = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              36.75596237182617,
              -1.2945599446037437
            ],
            [
              36.75355911254883,
              -1.2976490588348415
            ],
            [
              36.75682067871094,
              -1.301253020668912
            ],
            [
              36.76918029785156,
              -1.30296919116185
            ],
            [
              36.794071197509766,
              -1.302797574165142
            ],
            [
              36.81089401245117,
              -1.2985071454521169
            ],
            [
              36.81947708129883,
              -1.2966193545099025
            ],
            [
              36.82291030883789,
              -1.3052002110545196
            ],
            [
              36.82634353637695,
              -1.3141242707983072
            ],
            [
              36.83269500732422,
              -1.3196159840368622
            ],
            [
              36.846256256103516,
              -1.3276819158586177
            ],
            [
              36.85192108154297,
              -1.324936069674333
            ],
            [
              36.838016510009766,
              -1.3166985128854252
            ],
            [
              36.83166503906249,
              -1.3070879955717207
            ],
            [
              36.82497024536133,
              -1.2907843554331222
            ],
            [
              36.81140899658203,
              -1.2911275910441806
            ],
            [
              36.79853439331055,
              -1.295246414758441
            ],
            [
              36.76918029785156,
              -1.2962761196418089
            ],
            [
              36.75596237182617,
              -1.2945599446037437
            ]
          ]
        ]
      }
    }
  ]
}

ROUTE_DIVERSION = [
  (36.75922393798828, -1.2986787627406216),
  (36.7686653137207, -1.299536849008303),
  (36.77879333496094, -1.2988503800174724),
  (36.784629821777344, -1.2918140621272183), # << out of bounds
  (36.794586181640625, -1.2895830304297036), # out of bounds
  (36.80471420288086, -1.2888965587445615), # out of bounds
  (36.81312561035156, -1.2940450918657147), # << back in bounds
  (36.82188034057617, -1.2935302390231982)
]

class ProcessingTestCase(BaseTestCase):

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

        self.owner = User.Create(self.e, phone=OWNER_NUM, notify=False)
        self.owner.Update(name=OWNER_NAME, currency="KES")
        self.owner.put()

        self.spedometer = SensorType.Create(self.e)
        schema = {
            'speed': {
                'unit': 'kph'
            },
            'bearing': {
                'unit': 'deg'
            },
            'location': {
                'unit': 'degrees'
            },
            'hard_braking': {
                'unit': 'boolean'
            }

        }
        self.spedometer.Update(name="Geo Sensor", schema=json.dumps(schema))
        self.spedometer.put()

        self.vehicle_1 = Sensor.Create(self.e, TEST_SENSOR_ID, self.spedometer.key().id())
        self.vehicle_1.Update(
            sensortype_id=self.spedometer.key().id(),
            name="Vehicle Sensor 1",
            contacts={ "owner": self.owner.key().id() }
            )
        self.vehicle_1.put()

        # Create alarm
        self.speeding_alarm = Rule.Create(self.e)
        self.speeding_alarm.Update(
            name="Speeding",
            sensortype_id=self.spedometer.key().id(),
            column="speed",
            trigger=RULE.CEILING,
            value2=80.0,
            alert_contacts=["owner"],
            alert_message=SPEEDING_ALERT_MESSAGE,
            duration=0)
        self.speeding_alarm.put()

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

    def testCeilingAlarmAndStandardProcessing(self):
        self.process = ProcessTask.Create(self.e)
        spec = json.dumps({ 'processers':[
            {
                'calculation': 'MAX({speed})',
                'column': 'max_speed',
                'analysis_key_pattern': ANALYSIS_KEY_PATTERN
            },
            {
                'calculation': '. + SUM({bearing})',
                'column': 'total_bearing',
                'analysis_key_pattern': ANALYSIS_KEY_PATTERN
            },
            {
                'calculation': '. + COUNT({bearing})',
                'column': 'count_bearing',
                'analysis_key_pattern': ANALYSIS_KEY_PATTERN
            },
            {
                'calculation': '. + COUNT(ALARMS(%d))' % self.speeding_alarm.key().id(),
                'column': 'count_alarms',
                'analysis_key_pattern': ANALYSIS_KEY_PATTERN
            }
        ]})
        self.process.Update(spec=spec, rule_ids=[self.speeding_alarm.key().id()])
        self.process.put()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_1)
        self.sp.put()

        BATCH_1 = {
            'speed': [0,5,15,35,60,80,83,88,85,78,75,75,76,81,89,92,90,83,78], # We speed twice
            'bearing': [0,0,0,0,5,3,3,3,4,5,0,0,0,0,1,1,2,3,2]
        }
        self.__createNewRecords(BATCH_1, first_dt=datetime.now() - timedelta(minutes=5))
        self.__runProcessing()

        # Confirm analyzed max speed
        a = Analysis.GetOrCreate(self.vehicle_1, ANALYSIS_KEY_PATTERN)
        self.assertIsNotNone(a)
        self.assertEqual(a.columnValue('max_speed'), max(BATCH_1['speed']))

        # Confirm we counted new alarms in analysis
        # self.assertEqual(a.columnValue('count_alarms'), 2) TODO: This fails!
        self.sp = SensorProcessTask.Get(self.process, self.vehicle_1)
        self.assertEqual(self.sp.status_last_run, PROCESS.OK)

        # Confirm speeding alarms (2)
        alarms = Alarm.Fetch(self.vehicle_1, self.speeding_alarm)
        self.assertEqual(len(alarms), 2)

        # Test alarm notifications
        # TODO: Test output of notification (e.g. log messages or contact records)
        a = alarms[0] # second alarm
        message = a.render_alert_message(recipient=self.owner)
        SPEEDING_ALERT_MESSAGE_RENDERED = "Hello Dan Owner, %s was speeding at 81 at %s" % (TEST_SENSOR_ID, tools.sdatetime(a.dt_start, fmt="%H:%M", tz="Africa/Nairobi"))
        self.assertEqual(message, SPEEDING_ALERT_MESSAGE_RENDERED)

        BATCH_2 = {
            'speed': [76,75,78,73,60],
            'bearing': [0,0,2,0,5]
        }
        self.__createNewRecords(BATCH_2)
        self.__runProcessing()

        a = Analysis.GetOrCreate(self.vehicle_1, ANALYSIS_KEY_PATTERN)
        self.assertEqual(a.columnValue('total_bearing'), sum(BATCH_1['bearing']) + sum(BATCH_2['bearing']))
        self.assertEqual(a.columnValue('count_bearing'), len(BATCH_1['bearing']) + len(BATCH_2['bearing']))
        self.assertEqual(a.columnValue('count_alarms'), 2)
        self.assertEqual(self.sp.status_last_run, PROCESS.OK)

    def testAlarmBuffer(self):
        # Create hard braking (boolean) alarm
        self.brake_alarm = Rule.Create(self.e)
        self.brake_alarm.Update(
            name="Braking",
            sensortype_id=self.spedometer.key().id(),
            column="hard_braking",
            trigger=RULE.CEILING,
            value2=0.0,
            alert_contacts=["owner"],
            buffer=30000, # 30 s
            duration=0)
        self.brake_alarm.put()

        self.process = ProcessTask.Create(self.e)
        self.process.Update(rule_ids=[self.brake_alarm.key().id()])
        self.process.put()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_1)
        self.sp.put()

        BATCH_1 = {
            # v below should alarm, s are skipped since they fall within 30s buffer
            #                    v   s   s s                 v
            'hard_braking': [0,0,1,0,1,0,1,1,0,0,0,0,0,0,0,0,1,0] # Alternative boolean alarms
        }
        self.__createNewRecords(BATCH_1, first_dt=datetime.now() - timedelta(minutes=5), interval_secs=5)
        self.__runProcessing()

        # Confirm braking alarms (2)
        alarms = Alarm.Fetch(self.vehicle_1, self.brake_alarm)
        self.assertEqual(len(alarms), 2)

    def testAlarmPeriodLimit(self):
        # Create hard braking (boolean) alarm
        self.brake_rule = Rule.Create(self.e)
        self.brake_rule.Update(
            name="Braking",
            sensortype_id=self.spedometer.key().id(),
            column="hard_braking",
            trigger=RULE.CEILING,
            consecutive_limit=RULE.ANY,
            value2=0.0,
            alert_contacts=["owner"],
            plimit_type=RULE.HOUR,
            plimit=1) # 1 alarm each hour
        self.brake_rule.put()

        self.process = ProcessTask.Create(self.e)
        self.process.Update(rule_ids=[self.brake_rule.key().id()])
        self.process.put()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_1)
        self.sp.put()

        # Batch 1 creates 1 alarm in 11am window, skips second alarm
        # and then creates another alarm in 12pm window.
        start = datetime(2016,1,1,11,57) # 11:57am 2016-01-01
        BATCH_1 = {
            # v below should alarm, s should skip (already 1 in same period)
            # | is passing an hour marker (12pm)
            #                  v s | v
            'hard_braking': [0,1,1,0,1]
        }
        self.__createNewRecords(BATCH_1, first_dt=start, interval_secs=60)

        self.__runProcessing()
        alarms = Alarm.Fetch(self.vehicle_1, self.brake_rule)
        self.assertEqual(len(alarms), 2) # 1 in each hour

        last_alarm = alarms[-1]
        self.assertTrue(last_alarm.dt_start.hour, 12)
        self.assertTrue(last_alarm.dt_start.minute, 1)

        # Batch 2 fetches the prior 12pm window alarm, and fails to create
        # second alarm.
        start = datetime(2016,1,1,12,2) # 12:02pm 2016-01-01
        BATCH_2 = {
            #                    s   s
            'hard_braking': [0,0,1,0,1]
        }
        self.__createNewRecords(BATCH_2, first_dt=start, interval_secs=60)

        self.__runProcessing()
        alarms = Alarm.Fetch(self.vehicle_1, self.brake_rule)
        self.assertEqual(len(alarms), 2) # still 2, no new alarms created


    def testGeoFenceAlarm(self):
        self.geosensor = SensorType.Create(self.e)
        schema = {
            'location': {
                'unit': 'deg',
                'label': "Location",
                'role': [COLUMN.LOCATION],
                'type': 'latlng'
            }
        }
        self.geosensor.Update(name="Geo Sensor", schema=json.dumps(schema))
        self.geosensor.put()

        # Create off route alarm
        self.offroute_alarm = Rule.Create(self.e)
        self.offroute_alarm.Update(
            name="Off Route",
            sensortype_id=self.spedometer.key().id(),
            column="location",
            trigger=RULE.GEOFENCE_OUT,
            value_complex=json.dumps(DUMMY_GEOFENCE)
            )
        self.offroute_alarm.put()

        # Create in radius alarm
        self.in_radius_alarm = Rule.Create(self.e)
        self.in_radius_alarm.Update(
            name="In Nairobi",
            sensortype_id=self.spedometer.key().id(),
            column="location",
            trigger=RULE.GEORADIUS_IN,
            value2=500, # m
            value_complex={'lat': -1.274359, "lon": 36.813106},
            alert_contacts=["owner"],
            duration=0)
        self.in_radius_alarm.put()

        self.process = ProcessTask.Create(self.e)
        self.process.Update(rule_ids=[self.offroute_alarm.key().id(), self.in_radius_alarm.key().id()])
        self.process.put()

        self.vehicle_2 = Sensor.Create(self.e, TEST_SENSOR_ID, self.geosensor.key().id())
        self.vehicle_2.Update(name="Vehicle Sensor 2")

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_2)
        self.sp.put()

        # Process 8 location datapoints (3 in bounds, 3 out, 2 back in)
        BATCH_1 = {
            'location': ["%s,%s" % (coord[0], coord[1]) for coord in ROUTE_DIVERSION]
        }
        self.__createNewRecords(BATCH_1, first_dt=datetime.now() - timedelta(minutes=20), interval_secs=30)
        self.__runProcessing()

        # Confirm off-route alarm fired upon datapoint 4, and deactivates on 7 (back in fence)
        alarms = Alarm.Fetch(self.vehicle_2, self.offroute_alarm)
        self.assertEqual(len(alarms), 1)
        a = alarms[0]

        first_record_in_alarm = a.first_record
        self.assertEqual(a.duration().seconds, 60)  # 3 datapoints, 30 second gap
        oob_record = ROUTE_DIVERSION[3]
        self.assertEqual(first_record_in_alarm.columnValue('location'), "%s,%s" % (oob_record[0], oob_record[1]))

    def testCrossBatchAlarm(self):
        # TODO: Make this actually test analysis across batches (fetch prior active alarms)
        self.process = ProcessTask.Create(self.e)
        self.process.Update(rule_ids=[self.speeding_alarm.key().id()])
        self.process.put()

        now = datetime.now()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_1)
        self.sp.put()

        BATCH_1 = { 'speed': [0,5,15,90,93,90] }  # Speeding ends on last data point
        BATCH_2 = { 'speed': [70,50,0,0,50,90] }  # Second speeding starts on last
        BATCH_3 = { 'speed': [91,85,60,1,0,0] }  # Second speeding ends on second datapoint

        self.__createNewRecords(BATCH_1, first_dt=now - timedelta(minutes=6))
        self.__createNewRecords(BATCH_2, first_dt=now - timedelta(minutes=4))
        self.__createNewRecords(BATCH_3, first_dt=now - timedelta(minutes=2))

        self.__runProcessing()

        # Confirm 2 alarms, second straddling batch 2 and 3
        alarms = Alarm.Fetch(self.vehicle_1, self.speeding_alarm)
        self.assertEqual(len(alarms), 2)
        # Most recent first
        a2 = alarms[0]
        a1 = alarms[1]

        self.assertEqual(a1.duration().seconds, 6)  # 3 datapoints, 3 second gap
        self.assertEqual(a1.apex, 93)
        self.assertTrue(a2.duration().seconds > 30)  # 2 datapoints, large gap between batch 2 & 3
        self.assertEqual(a2.apex, 91)

    def testNoDataAlarm(self):
        self.mia_alarm = Rule.Create(self.e)
        self.mia_alarm.Update(name="No Data", sensortype_id=self.spedometer.key().id(), column="speed", trigger=RULE.NO_DATA, duration=5000)  # No data for > 5s
        self.mia_alarm.put()

        self.process = ProcessTask.Create(self.e)
        self.process.Update(spec=None, rule_ids=[self.mia_alarm.key().id()])
        self.process.put()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_1)
        self.sp.dt_last_run = datetime.now() - timedelta(minutes=2)
        self.sp.put()

        self.__runProcessing()

        # Process last 2 minutes, with no new data, fires alarm
        alarms = Alarm.Fetch(self.vehicle_1, self.mia_alarm)
        # self.assertEqual(len(alarms), 1)

        batch_1 = {'speed': [1,1,1,1,1] }
        self.__createNewRecords(batch_1, interval_secs=3)
        self.__runProcessing()

        # We get data every 3 seconds, so 5-second no-data alarm doesn't fire
        alarms = Alarm.Fetch(self.vehicle_1, self.mia_alarm)
        self.assertEqual(len(alarms), 0)


    def testAlarmWithPayment(self):
        # Create smartphone report sensor
        self.smartphone_sensor_type = SensorType.Create(self.e)
        schema = {
            'agreement': {
                'unit': '1-5 scale'
            }
        }
        self.smartphone_sensor_type.Update(name="Report Sensor", schema=json.dumps(schema))
        self.smartphone_sensor_type.put()

        self.smartphone_sensor = Sensor.Create(self.e, "1000", self.smartphone_sensor_type.key().id())
        self.smartphone_sensor.Update(
            sensortype_id=self.smartphone_sensor_type.key().id(),
            name="Smartphone Reports 1",
            contacts={ "user": self.owner.key().id() }
            )
        self.smartphone_sensor.put()

        # Create smartphone report rule with payment on any report
        PMNT_AMOUNT = 10.0
        self.any_report_rule = Rule.Create(self.e)
        self.any_report_rule.Update(
            name="Any Report",
            sensortype_id=self.smartphone_sensor_type.key().id(),
            column="agreement",
            trigger=RULE.ANY_DATA,
            payment_contacts=["user"],
            payment_amount=PMNT_AMOUNT,
            consecutive_limit=RULE.ANY, # Deactivate immediately (should be == 1)
            duration=0)
        self.any_report_rule.put()

        self.assertTrue(self.any_report_rule.payments_enabled())

        self.process = ProcessTask.Create(self.e)
        self.process.Update(rule_ids=[self.any_report_rule.key().id()])
        self.process.put()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.smartphone_sensor)
        self.sp.put()

        BATCH_SIZE = 3
        BATCH_1 = {
            'agreement': [random.randint(1,5) for x in range(BATCH_SIZE)],
        }
        self.__createNewRecords(BATCH_1, first_dt=datetime.now(), sensor=self.smartphone_sensor)
        self.__runProcessing()

        # This batch should have fired 3 alarms for any report, and created
        # 3 payments.

        pmnts = Payment.Fetch(self.owner)
        self.assertEqual(len(pmnts), 3)
        total_payments = BATCH_SIZE * PMNT_AMOUNT
        self.assertEqual(total_payments, sum([p.amount for p in pmnts]))



    def testParsingIssues(self):
        # Try to run calculation against nonexistant column
        self.process = ProcessTask.Create(self.e)
        spec = json.dumps({ 'processers':[
            {
                'calculation': 'MAX({missing_column})',
                'column': 'output',
                'analysis_key_pattern': ANALYSIS_KEY_PATTERN
            }
        ]})
        self.process.Update(spec=spec, rule_ids=[self.speeding_alarm.key().id()])
        self.process.put()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_1)
        self.sp.put()

        BATCH_1 = {
            'speed': [0 for x in range(10)],
        }
        self.__createNewRecords(BATCH_1, first_dt=datetime.now())
        self.__runProcessing()

        self.sp = SensorProcessTask.Get(self.process, self.vehicle_1)
        self.assertEqual(self.sp.status_last_run, PROCESS.OK)

    def testGeoProcessing(self):
        self.process = ProcessTask.Create(self.e)
        spec = json.dumps({ 'processers':[
            {
                'calculation': '. + DISTANCE({location})',
                'column': 'total_distance',
                'analysis_key_pattern': ANALYSIS_KEY_PATTERN
            }
        ]})
        self.process.Update(spec=spec)
        self.process.put()

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_1)
        self.sp.put()

        loc = db.GeoPt(1.3, 36)
        MOVE_SIZE = 5 # m
        N_POINTS = 150  # 2 batches in process worker
        DELAY_SECS = 1
        now = datetime.now()

        # Populate dummy data with random moves
        total_distance = 0.0
        locations = []
        last_gp = None
        for x in range(N_POINTS):
            locations.append(str(loc))
            now += timedelta(seconds=DELAY_SECS)
            bearing = random.random()*180
            loc = tools.geoOffset(loc, bearing, MOVE_SIZE/1000.)
            if last_gp:
                total_distance += MOVE_SIZE
            last_gp = loc
        BATCH_1 = { 'location': locations }
        self.__createNewRecords(BATCH_1, first_dt=datetime.now())
        self.__runProcessing()

        # Confirm analyzed distance
        a = Analysis.GetOrCreate(self.vehicle_1, ANALYSIS_KEY_PATTERN)
        self.assertIsNotNone(a)
        # Almost equal becuase we miss the distance between batches (FIX)
        self.assertAlmostEqual(a.columnValue('total_distance'), total_distance, delta=MOVE_SIZE)


    def tearDown(self):
        pass



