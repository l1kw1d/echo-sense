#!/usr/bin/python
# -*- coding: utf8 -*-

from google.appengine.ext import db

from datetime import datetime, timedelta
import tools
import json
import logging
from constants import REPORT
from models import Enterprise, SensorType, Sensor, Record, User, Report
from base_test_case import BaseTestCase
from echosense import app as tst_app
import cloudstorage

TEST_SENSOR_ID = "00-100"
ANALYSIS_KEY_PATTERN = '%SID_%Y-%M-%D'
OWNER_NAME = "Dan Owner"
OWNER_NUM = "254700000000"
SPEEDING_ALERT_MESSAGE = "Hello {to.name}, {sensor.id} was speeding at {record.first.alarm_value} at {start.time}"

class ReportsTestCase(BaseTestCase):

    def setUp(self):
        self.set_application(tst_app)
        self.setup_testbed()
        self.init_datastore_stub()
        self.init_memcache_stub()
        self.init_taskqueue_stub()
        self.init_app_identity_stub()
        self.init_mail_stub()
        self.register_search_api_stub()
        self.init_urlfetch_stub()
        self.init_blobstore_stub()
        self.init_modules_stub()
        cloudstorage.set_default_retry_params(None)


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
            'narrative': {
                'type': 'string'
            }
        }
        self.spedometer.Update(name="Spedometer", schema=json.dumps(schema))
        self.spedometer.put()

        self.vehicle_1 = Sensor.Create(self.e, TEST_SENSOR_ID, self.spedometer.key().id())
        self.vehicle_1.Update(
            sensortype_id=self.spedometer.key().id(),
            name="Vehicle Sensor 1"
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
            now += timedelta(seconds=interval_secs)
            r = Record.Create(tools.unixtime(now), sensor, _r, allow_future=True)
            records.append(r)
        db.put(records)
        sensor.dt_updated = datetime.now()
        sensor.put()
        logging.debug("Created %d records" % len(records))
        if records:
            return records[-1].dt_recorded # Datetime of last record created
        else:
            return None


    def testReportGeneration(self):

        # With non-ascii text in batch
        BATCH_1 = {
            'speed': [0 for x in range(10)],
            'narrative': [None, None, "Narrative", "Test", "", u"Làst", None, None, None, None]
        }
        self.__createNewRecords(BATCH_1, first_dt=datetime.now())

        specs = {
            'sensortype_id': self.spedometer.key().id(),
            'columns': ['narrative', 'speed']
        }
        r = Report.Create(self.e, type=REPORT.SENSOR_DATA_REPORT, specs=specs)
        r.put()
        r.run(None)

        self.execute_tasks_until_empty()

        r = Report.get(r.key())
        self.assertTrue(r.isDone())


    def tearDown(self):
        pass



