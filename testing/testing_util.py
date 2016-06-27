#!/usr/bin/python
# -*- coding: utf8 -*-

import unittest
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed
from expressionParser import ExpressionParser
from datetime import datetime, timedelta
import tools
import json
import math
from google.appengine.ext import deferred
from base_test_case import BaseTestCase
import logging
import os
from echosense import app as tst_app

class UtilTestCase(BaseTestCase):

    def setUp(self):
        self.set_application(tst_app)
        self.setup_testbed()
        self.init_datastore_stub()
        self.init_memcache_stub()
        self.init_taskqueue_stub()
        self.register_search_api_stub()


    def testValidJson(self):
        volley=[
            {'json':"{}",'to_return':{}},
            {'json':'{"v":"1"}','to_return':{"v":"1"}},
            {'json':'{"v":"1"\r\n}','to_return':{"v":"1"}},
            {'json':'{"v":1}','to_return':{"v":1}},
            {'json':'"{}"','to_return':{}},
            {'json': "invalid", 'to_return': None},
            {'json': '[{"1":"one"}]', 'to_return': [{1:"one"}] }
        ]

        for v in volley:
            returned = tools.getJson(v['json'])
            self.assertEqual(json.dumps(returned),json.dumps(v['to_return']))

    def testSafeNum(self):
        volley=[
            ("1,000", 1000),
            ("not a number", None),
            ("2.56", 2.56),
            ("4", 4),
            ("0", 0),
            ("11.0", 11.0)
        ]

        for v in volley:
            _in, _expect = v
            out = tools.safe_number(_in)
            self.assertEqual(out, _expect)

    def testExpressionParsing(self):
        from models import Record
        r = Record()
        x = 5
        y = -2
        z = 3.5
        r.setColumnValue("x", x)
        r.setColumnValue("y", y)
        r.setColumnValue("z", z)
        now_ms = tools.unixtime()
        volley = [
            ["1 + 1", (1 + 1) ],
            ["1 + 1 + 5", (1 + 1 + 5) ],
            ["2 * 8 + 3", (2*8) + 3 ],
            ["4 + 5 * 2", 4 + (5*2)],
            ["2^3", (pow(2,3)) ],
            ["(8/2)*3 + 9", ((8/2)*3 + 9) ],
            ["[x]^2", (pow(x,2))],
            ["SQRT([x]^2 + [y]^2)", math.sqrt(pow(x,2)+pow(y,2)) ],
            ["5 > 2", True],
            ["5 > 6", False],
            ["(3*5) < 20", True],
            ["[x] > 100", False],
            ["(3*5) < 20 AND [x] > 100", False],
            ["(3*5) < 20 AND [x] > 0 AND [x] > 1", True],
            ["1==1 OR 1==3 AND 2==0", True],
            ["(1==1 OR 1==3) AND 2==2", True],
            ["(1==2 AND 1==3) OR 2==2", True],
            ["(1==1 OR 1==1) AND 1==0", False],
            ["1==1 OR 1==1 AND 1==0", True], # And first
            ["1==1 OR (1==1 AND 1==0)", True],
            ["1 == 2 OR [x] > 100 OR [x] > 1", True],
            ["1==2 OR 1==1 OR 1==4 OR 1==5", True],
            ["SINCE(1467011405000)", now_ms - 1467011405000],
            ["SQRT([x]^2 + [y]^2)", ( math.sqrt(pow(x,2)+pow(y,2)) )],
            ["SQRT([x]^2 + [y]^2 + 8^2)", ( math.sqrt(pow(x,2)+pow(y,2)+pow(8,2))) ],
            ["SQRT([x]^2 + [y]^2 + [z]^2)", ( math.sqrt(pow(x,2)+pow(y,2)+pow(z,2))) ]
        ]

        for v in volley:
            expr = v[0]
            target = v[1]
            tick = datetime.now()
            ep = ExpressionParser(expr, verbose=True, run_ms=now_ms)
            result = ep.run(r)
            tock = datetime.now()
            diff = tock - tick
            ms = diff.microseconds/1000
            logmessage = "%s took %d ms" % (expr, ms)
            if ms > 100:
                logmessage += " <<<<<<<<<<<<<<<<<<<<<<<<<<< SLOW OP!"
            print logmessage
            self.assertEqual(result, target)

    def testTextSanitization(self):
        # Remove non-ascii
        from decimal import Decimal
        volley = [
            ('‘Hello’', 'Hello'),
            (int(10), '10'),
            (False, 'False'),
            (long(20), '20'),
            (u'‘Hello’', 'Hello'),
            (u'‘Hello\nHi’', 'Hello\nHi'),
            (u'Kl\xfcft skr\xe4ms inf\xf6r p\xe5 f\xe9d\xe9ral \xe9lectoral gro\xdfe',
               'Kluft skrams infor pa federal electoral groe'),
            (db.Text(u'‘Hello’'), 'Hello'),
            (db.Text(u'naïve café'), 'naive cafe')
        ]

        for v in volley:
            target = v[1]
            actual = tools.normalize_to_ascii(v[0])
            self.assertEqual(actual, target)

    def testDateTimePrinting(self):
        volley = [
            ( datetime(2015,1,1,12,0), "UTC", "2015-01-01 12:00 UTC" ),
            ( datetime(2015,1,1,12,25), "Africa/Nairobi", "2015-01-01 15:25 EAT" ),
            ( datetime(2015,1,25,4,21), None, "2015-01-25 04:21 UTC" ),
        ]

        for v in volley:
            dt = v[0]
            tz = v[1]
            target = v[2]
            result = tools.sdatetime(dt, tz=tz)
            self.assertEqual(result, target)

    def testDecimals(self):
        from tools import toDecimal
        volley = [
            ( 50, "50" )
            # ( 25.2, "25.2" ),
        ]

        for v in volley:
            num, dec = v
            out = toDecimal(num)
            self.assertEqual(str(out), dec)

    def testLastMonday(self):
        volley = [
            (datetime(2016, 3, 31), "2016-03-28"),
            (datetime(2016, 3, 6, 2, 15), "2016-02-29"),
            (datetime(2015, 10, 7, 14, 0), "2015-10-05"),
            (datetime(2015, 7, 20, 14, 0), "2015-07-20")
        ]
        for v in volley:
            today, last_monday = v
            out = tools.last_monday(today)
            self.assertEqual(tools.sdate(out), last_monday)
        self.assertEqual(tools.stime(out.time()), "00:00")

    def testInSamePeriod(self):
        from constants import RULE
        volley = [
            # dt1, dt2, period_type, expect same (bool)
            (datetime(2016, 3, 31, 12, 15), datetime(2016, 3, 31, 12, 55), RULE.HOUR, True),
            (datetime(2016, 3, 31, 11, 58), datetime(2016, 3, 31, 12, 2), RULE.HOUR, False),
            (datetime(2016, 3, 31, 11, 58, 59), datetime(2016, 3, 31, 11, 58, 13), RULE.MINUTE, True),
            (datetime(2016, 3, 29), datetime(2016, 4, 1), RULE.WEEK, True),
            (datetime(2016, 3, 29), datetime(2016, 4, 4), RULE.WEEK, False),
            (datetime(2016, 1, 2), datetime(2016, 1, 28), RULE.MONTH, True),
            (datetime(2016, 1, 29), datetime(2015, 1, 4), RULE.MONTH, False)
        ]
        for v in volley:
            dt1, dt2, period_type, same = v
            ms1, ms2 = tools.unixtime(dt1), tools.unixtime(dt2)
            out = tools.in_same_period(ms1, ms2, period_type)
            self.assertEqual(out, same)

    def testInRadius(self):
        center_lat = 1.2
        center_lon = 32.0
        volley = [
            # lat, lon, radius, inside (boolean)
            (1.2, 32.0, 10, True),
            (1.2, 33.0, 10, False),
            # TODO: Add tests
        ]

        for v in volley:
            lat, lon, radius, expect_inside = v
            inside = tools.point_within_radius(lat, lon, center_lat, center_lon, radius_m=radius)
            self.assertEqual(inside, expect_inside)


    def tearDown(self):
        pass



