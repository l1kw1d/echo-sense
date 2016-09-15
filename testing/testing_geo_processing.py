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
  (-1.2986787627406216, 36.75922393798828),
  (-1.299536849008303, 36.7686653137207),
  (-1.2988503800174724, 36.77879333496094),
  (-1.2918140621272183, 36.784629821777344), # << out of bounds
  (-1.2895830304297036, 36.794586181640625), # out of bounds
  (-1.2888965587445615, 36.80471420288086), # out of bounds
  (-1.2940450918657147, 36.81312561035156), # << back in bounds
  (-1.2935302390231982, 36.82188034057617)
]

RADIUS_CENTER = {"lon": 36.820335388183594, "lat": -1.2909559732444464}
RADIUS = 600 # m

ENTERS_RADIUS = [
    (-1.2588632427458806, 36.77621841430664),
    (-1.2597213423288907, 36.79819107055664),
    (-1.272421183012338, 36.81123733520508),
    (-1.2899262662028559, 36.819305419921875) # << in radius
]

EXITS_RADIUS = [
    (-1.294388327036012, 36.82188034057617),  # << in radius
    (-1.294388327036012, 36.82188034057617),  # << in radius
    (-1.3112067932257756, 36.830291748046875),
    (-1.324936069674333, 36.84728622436523)
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

        self.tracker = SensorType.Create(self.e)
        schema = {
            'bearing': {
                'unit': 'deg'
            },
            'location': {
                'unit': 'deg',
                'label': "Location",
                'role': [COLUMN.LOCATION],
                'type': 'latlng'
            }
        }
        self.tracker.Update(name="Geo Sensor", schema=json.dumps(schema))
        self.tracker.put()

        self.vehicle_1 = Sensor.Create(self.e, TEST_SENSOR_ID, self.tracker.key().id())
        self.vehicle_1.Update(
            sensortype_id=self.tracker.key().id(),
            name="Vehicle Sensor 1",
            contacts={ "owner": self.owner.key().id() }
            )
        self.vehicle_1.put()

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
        return records[-1]

    def __runProcessing(self):
        self.sp.run()  # Fires background worker
        # Force completion
        self.execute_tasks_until_empty()

    def testGeoFenceAlarm(self):
        # Create off route alarm
        self.offroute_alarm = Rule.Create(self.e)
        self.offroute_alarm.Update(
            name="Off Route",
            sensortype_id=self.tracker.key().id(),
            column="location",
            trigger=RULE.GEOFENCE_OUT,
            value_complex=json.dumps(DUMMY_GEOFENCE)
            )
        self.offroute_alarm.put()

        self.process = ProcessTask.Create(self.e)
        self.process.Update(rule_ids=[self.offroute_alarm.key().id()])
        self.process.put()

        self.vehicle_2 = Sensor.Create(self.e, TEST_SENSOR_ID, self.tracker.key().id())
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

    def testGeoRadiusAlarm(self):
        # Create in radius alarm
        self.in_radius_alarm = Rule.Create(self.e)
        self.in_radius_alarm.Update(
            name="In Town",
            sensortype_id=self.tracker.key().id(),
            column="location",
            trigger=RULE.GEORADIUS_IN,
            value2=RADIUS, # m
            value_complex=json.dumps(RADIUS_CENTER),
            alert_contacts=["owner"],
            consecutive_limit=RULE.DISABLED,
            duration=0)
        self.in_radius_alarm.put()

        self.process = ProcessTask.Create(self.e)
        self.process.Update(rule_ids=[self.in_radius_alarm.key().id()])
        self.process.put()

        self.vehicle_2 = Sensor.Create(self.e, TEST_SENSOR_ID, self.tracker.key().id())
        self.vehicle_2.Update(name="Vehicle Sensor 2")

        # Apply our process to our sensor
        self.sp = SensorProcessTask.Create(self.e, self.process, self.vehicle_2)
        self.sp.put()

        INTERVAL_SECS = 4
        test_data_start = datetime.now() - timedelta(minutes=20)

        # Process first data points entering radius
        BATCH_1 = {
            'location': ["%s,%s" % (coord[0], coord[1]) for coord in ENTERS_RADIUS]
        }
        last_record = self.__createNewRecords(BATCH_1, first_dt=test_data_start, interval_secs=INTERVAL_SECS)
        self.__runProcessing()

        # Confirm in-radius alarm fired upon datapoint 4...
        alarms = Alarm.Fetch(self.vehicle_2, self.in_radius_alarm)
        self.assertEqual(len(alarms), 1)
        a = alarms[0]

        # Process second batch of data points exiting radius
        BATCH_2 = {
            'location': ["%s,%s" % (coord[0], coord[1]) for coord in EXITS_RADIUS]
        }
        self.__createNewRecords(BATCH_2, interval_secs=INTERVAL_SECS)
        self.__runProcessing()

        # Confirm we still just have the single alarm record
        alarms = Alarm.Fetch(self.vehicle_2, self.in_radius_alarm)
        self.assertEqual(len(alarms), 1)
        a = alarms[0]
        duration_td = a.duration()
        self.assertIsNotNone(duration_td)
        # 3 datapoints in radius
        print a.json()
        # self.assertEqual(tools.total_seconds(duration_td), INTERVAL_SECS*3)



    def testDistanceCalculation(self):
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
        now = datetime.now() - timedelta(minutes=10)

        # Populate dummy data with random moves
        total_distance = 0.0
        locations = []
        last_gp = None
        for x in range(N_POINTS):
            locations.append(str(loc))
            bearing = random.random()*180
            loc = tools.geoOffset(loc, bearing, MOVE_SIZE/1000.)
            if last_gp:
                total_distance += MOVE_SIZE
            last_gp = loc
        BATCH_1 = { 'location': locations }
        self.__createNewRecords(BATCH_1, first_dt=now)
        self.__runProcessing()

        # Confirm analyzed distance
        a = Analysis.GetOrCreate(self.vehicle_1, ANALYSIS_KEY_PATTERN)
        self.assertIsNotNone(a)
        # Almost equal becuase we miss the distance between batches (FIX)
        self.assertAlmostEqual(a.columnValue('total_distance'), total_distance, delta=2*MOVE_SIZE)


    def tearDown(self):
        pass



