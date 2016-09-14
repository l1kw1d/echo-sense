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

    def testInPolygon(self):
        # With nonstandard longs
        STANDARD_POLYGON = [[36.938438415527344, -1.2360376907734281], [36.936357021331787, -1.2358875220147409], [36.92753791809082, -1.2319187731748422], [36.921250820159912, -1.2288939390070786], [36.911680698394775, -1.2220290544409012], [36.908268928527832, -1.2231445993794376], [36.903183460235596, -1.2180388322173765], [36.904256343841553, -1.214112962650395], [36.903462409973145, -1.2117102418505807], [36.897132396697998, -1.2137053583792856], [36.894171237945557, -1.2160651717280586], [36.890544891357422, -1.2194547181998101], [36.888248920440674, -1.2218145265149736], [36.885309219360352, -1.224453218812366], [36.882069110870361, -1.2268130227320284], [36.875953674316406, -1.2315111716075733], [36.872456073760986, -1.2329699558763181], [36.871790885925286, -1.2346218135684603], [36.870138645172112, -1.2369816084907406], [36.86887264251709, -1.2397490016801844], [36.867413520812988, -1.2433315916669363], [36.866040229797356, -1.2439108123463127], [36.865932941436768, -1.2449190850774554], [36.863465309143066, -1.246935629382693], [36.853680610656738, -1.2562031322446616], [36.84938907623291, -1.2573615677961414], [36.845440864562988, -1.2579193328783678], [36.838874816894531, -1.2615662554751739], [36.836600303649895, -1.263325357489324], [36.834368705749512, -1.2655993168643884], [36.831750869750977, -1.2665432239441321], [36.829218864440918, -1.2670580822063775], [36.825485229492188, -1.2679161790826974], [36.821494102478027, -1.2681307032573386], [36.815314292907715, -1.2649986485438416], [36.812009811401367, -1.2643979800842535], [36.808018684387207, -1.2626388787961478], [36.806216239929199, -1.262810498486429], [36.804499626159668, -1.261694970297037], [36.803555488586419, -1.2607939664102334], [36.803126335144043, -1.2610084911734809], [36.80269718170166, -1.2620382097909038], [36.802482604980469, -1.2629821181654004], [36.800851821899414, -1.264827028998148], [36.803727149963379, -1.2677874645693861], [36.806087493896484, -1.2706191823830455], [36.807804107666016, -1.2725928020542696], [36.809349060058594, -1.2737083255483743], [36.810421943664551, -1.2758964663837939], [36.813039779663086, -1.2758964663837939], [36.813340187072754, -1.2743089918452106], [36.81492805480957, -1.2733221828550407], [36.816473007202148, -1.2725069925347288], [36.815357208251953, -1.271863421047233], [36.815872192382812, -1.27074789675542], [36.818790435791016, -1.2697610864033493], [36.820893287658691, -1.269632371981829], [36.823639869689941, -1.2692033238637983], [36.82767391204834, -1.2688600853181182], [36.835269927978516, -1.2670151773550962], [36.83866024017334, -1.2638831212939725], [36.841320991516113, -1.2631537378330235], [36.842093467712402, -1.2619523999216926], [36.848015785217285, -1.2588632427458806], [36.853938102722168, -1.2587774327720291], [36.857800483703613, -1.2554308415916193], [36.863293647766113, -1.2501535160309447], [36.867413520812988, -1.2458200944258819], [36.868529319763184, -1.2455626632149055], [36.868486404418945, -1.2449190850774554], [36.869645118713372, -1.2429883497228846], [36.870675086975098, -1.2402853178553541], [36.872777938842766, -1.2362522175568367], [36.88011646270752, -1.2307603264520459], [36.886124610900879, -1.2261694400510923], [36.891145706176758, -1.2210636786393594], [36.892862319946289, -1.2215785457766755], [36.896252632141113, -1.2190900203664174], [36.89784049987793, -1.2181460963330069], [36.901745796203613, -1.2193045485096912], [36.90281867980957, -1.2198194159837772], [36.904363632202148, -1.2215785457766755], [36.908140182495117, -1.2250109908355553], [36.911830902099609, -1.2237238244530939], [36.920285224914544, -1.230030933812843], [36.928439140319824, -1.2338924219867029], [36.937322616577148, -1.2376680938924316], [36.938438415527344, -1.2360376907734281]]

        volley = [
            # lat, lon, radius, inside (boolean)
            (-1.2161295302450534, 36.90084457397461, STANDARD_POLYGON, True),
            (12.0, -5.0, STANDARD_POLYGON, False)
        ]

        for v in volley:
            lat, lon, polygon, expect_inside = v
            print lat, lon
            inside = tools.point_inside_polygon(lon, lat, polygon)
            self.assertEqual(inside, expect_inside)

    def testRuntimeBatching(self):
        now = datetime(2016, 4, 3, 12, 2) # April 3 12:02pm

        for i in range(4):
            new_now = now + i*timedelta(seconds=30)
            runAt = tools.batched_runtime_with_jitter(now, interval_mins=5,
                max_jitter_pct=0.0, name_prefix="prefix1")
            # All scheduled for 12:05pm since no jitter pct
            self.assertEqual(runAt.minute, 5)
            self.assertEqual(runAt.hour, 12)

        prefix1_runs = []
        prefix2_runs = []
        for i in range(4):
            new_now = now + i*timedelta(seconds=30)
            runAt = tools.batched_runtime_with_jitter(now, interval_mins=5,
                max_jitter_pct=0.2, name_prefix="prefix1")
            prefix1_runs.append(runAt)
            runAt = tools.batched_runtime_with_jitter(now, interval_mins=5,
                max_jitter_pct=0.2, name_prefix="prefix2")
            prefix2_runs.append(runAt)

        # All prefix1 runs same, between 12:05 and 12:06
        self.assertEqual(len(set(prefix1_runs)), 1)

        # All prefix2 runs same, between 12:05 and 12:06
        self.assertEqual(len(set(prefix2_runs)), 1)

        print prefix1_runs
        print prefix2_runs

    def testThrottling(self):
        for i in range(5):
            expected = i == 0  # Not throttled first time only
            self.assertEqual(expected, tools.not_throttled("test_key"))

    def tearDown(self):
        pass



