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


    def testSimpleExpressionParsing(self):
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

    def testAggregatedExpressionParsing(self):
        from models import Record
        record_list = []
        start_ms = tools.unixtime()
        ts_data = [start_ms+x for x in range(0,100,10)] # 10 ms apart
        y_data = [0,0,1,1,1,1,0,0,0,0]
        for i, ts, y in zip(range(10), ts_data, y_data):
            r = Record()
            r.setColumnValue("ts", ts)
            r.setColumnValue("y", y)
            record_list.append(r)
        now_ms = tools.unixtime()
        import numpy as np
        volley = [
            ["DOT({ts},{y})", np.dot(ts_data, y_data)],
            ["MAX({y})", max(y_data)],
            ["MIN({y})", 0],
            ["COUNT({y})", 10],
            ["DOT(DELTA({ts}), {y})", 40] # 40ms
        ]

        for v in volley:
            expr = v[0]
            target = v[1]
            tick = datetime.now()
            ep = ExpressionParser(expr, verbose=True, run_ms=now_ms)
            result = ep.run(record_list=record_list)
            tock = datetime.now()
            diff = tock - tick
            ms = diff.microseconds/1000
            logmessage = "%s took %d ms" % (expr, ms)
            if ms > 100:
                logmessage += " <<<<<<<<<<<<<<<<<<<<<<<<<<< SLOW OP!"
            print logmessage
            self.assertEqual(result, target)

    def tearDown(self):
        pass



