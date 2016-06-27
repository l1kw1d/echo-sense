import tools
from constants import *
from models import *
from datetime import datetime
import gc
import logging
import random
from expressionParser import ExpressionParser
from google.appengine.api import logservice
from google.appengine.api import memcache
from google.appengine.api import search
from google.appengine.api import taskqueue
from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.runtime import DeadlineExceededError
import traceback
from decorators import deferred_task_decorator

MAX_REQUEST_SECONDS = 40 # TODO: Should this be 5 mins?

USE_DEFERRED = True

class TooLongError(Exception):
    def __init__(self):
        pass

# TODO
# Rearchitect to query in window (last run to now (when worker starts))
# Otherwise we may miss records coming in during processing

class SensorProcessWorker(object):

    def __init__(self, sensorprocess, batch_size=100):
        self.sensorprocess = sensorprocess
        self.batch_size = batch_size
        self.cursor = None
        self.start = datetime.now()
        self.sensor = sensorprocess.sensor
        self.ent = sensorprocess.enterprise
        self.process = sensorprocess.process
        self.dt_last_run = sensorprocess.dt_last_run
        self.query = self.sensor.record_set.filter('dt_recorded >', self.dt_last_run).order('dt_recorded')
        self.processers = self.process.get_processers()  # JSON array of <processer>
        self.ep = None
        self.analyses = {}
        self.last_record = None
        logging.debug("Initializing %s" % self)

    def __str__(self):
        return "<SensorProcessWorker last_run=%s />" % (self.dt_last_run)


    def setup(self):
        self.rules = self.process.get_rules()  # Rules active for this process
        if self.processers:
            # Fetch analyses used (if any) in any processers
            # Note that this does not fetch analysis keys defined in rules
            for processer in self.processers:
                self._get_or_create_analysis(processer['analysis_key_pattern'])

        # Alarm & Condition State
        self.condition_consecutive = [0 for r in self.rules]  # Maintain # of consecutive records where each condition passes
        self.condition_start_ts = [None for r in self.rules]  # Maintain timestamp when condition started passing
        self.recent_alarms = self.fetch_recent_alarms() # List of most recent alarms (if period limited, in period up to limit) for each rule
        self.greatest_rule_diff = [0 for r in self.rules]  # Maintain largest diff (depth out of rule range)
        self.updated_alarm_dict = {}  # Stores alarms needing put upon finish()
        self.active_rules = []
        for i, r in enumerate(self.rules):
            active_alarm = self._recent_active_alarm(i)
            # One Alarm() for each rule, or None
            self.active_rules.append(active_alarm)

    def _get_or_create_analysis(self, key_pattern):
        a = None
        akn = Analysis._key_name(key_pattern, self.sensor)
        if akn in self.analyses:
            a = self.analyses.get(akn)
        else:
            a = Analysis.GetOrCreate(self.sensor, key_pattern)
            if a:
                self.analyses[akn] = a
        return a

    def _recent_active_alarm(self, rule_index):
        alarms = self.recent_alarms[rule_index]
        if alarms:
            alarms = filter(lambda al : al.active(), alarms)
            if alarms:
                return alarms[0]
        return None


    def last_activation_ts(self, rule_index):
        alarms = self.recent_alarms[rule_index]
        if alarms:
            last_alarm = alarms[0]
            if last_alarm:
                return toolx.unixtime(last_alarm.dt_start)
        return None

    def last_deactivation_ts(self, rule_index):
        alarms = self.recent_alarms[rule_index]
        if alarms:
            last_alarm = alarms[0]
            if last_alarm:
                return tools.unixtime(last_alarm.dt_end)
        return None

    def fetch_recent_alarms(self):
        '''Fetch most recent alarms for each rule.

        If a period limit is active, fetch up to plimit alarms since beginning of current period,
        so we can identify if current period limit has been reached.

        As processing continues, these lists will be extended with new alarms
        enabling continuing period limit checks.

        Returns:
            list: list of lists (Recent Alarm() objects at each rule index, ordered desc. by dt_start)
        '''
        recent_alarms = []
        for r in self.rules:
            limit = r.plimit if r.period_limit_enabled() else 1
            recent_alarms.append(Alarm.Fetch(sensor=self.sensor, rule=r, limit=limit))
        return recent_alarms

    def fetchBatch(self):
        if self.cursor:
            self.query.with_cursor(self.cursor)
        batch = self.query.fetch(self.batch_size)
        logging.debug("Fetched batch of %d. Cursor: %s" % (len(batch), self.cursor))
        self.cursor = self.query.cursor()
        return batch

    def runBatch(self, records):
        # Standard processing (alarms)
        self.new_alarms = []
        for record in records:
            new_alarm = self.processRecord(record)
            if new_alarm:
                self.new_alarms.append(new_alarm)

        # Analysis processing
        if self.processers:
            for processer in self.processers:
                run_ms = tools.unixtime(records[-1].dt_recorded) if records else 0
                self._run_processer(processer, records=records, run_ms=run_ms)

        db.put(self.analyses.values())

        logging.debug("Ran batch of %d." % (len(records)))

    def __update_alarm(self, alarm, dt_end):
        alarm.dt_end = dt_end
        self.updated_alarm_dict[str(alarm.key())] = alarm

    def __buffer_ok(self, rule_index, record):
        ok = True
        rule = self.rules[rule_index]
        last_deactivation_ts = self.last_deactivation_ts(rule_index)
        if last_deactivation_ts is not None:
            buffer = record.ts() - last_deactivation_ts
            ok = buffer > rule.buffer
        return ok

    def __period_limit_ok(self, rule_index, record):
        ok = True
        rule = self.rules[rule_index]
        if rule.period_limit_enabled():
            period_count = rule.period_count(self.recent_alarms[rule_index], record)
            ok = period_count < rule.plimit
        return ok

    def __consecutive_ok(self, rule_index):
        rule = self.rules[rule_index]
        consecutive = self.condition_consecutive[rule_index]
        ok = consecutive >= rule.consecutive or rule.consecutive == RULE.DISABLED
        return ok

    def __duration_ok(self, rule_index, record):
        rule = self.rules[rule_index]
        start_ts = self.condition_start_ts[rule_index]
        record_ts = record.ts()
        if start_ts is None:
            start_ts = self.condition_start_ts[rule_index] = record_ts
        duration = record_ts - start_ts
        ok = duration >= rule.duration
        return ok

    def __update_condition_status(self, rule_index, record):
        activate = deactivate = False
        active_alarm = self.active_rules[rule_index]
        rule = self.rules[rule_index]
        record_ts = record.ts()
        passed, diff, val = rule.alarm_condition_passed(record, prior_r=self.last_record)
        force_clear = False
        if passed:
            if active_alarm:
                # Check of consecutive limit reached
                force_clear = rule.consecutive_limit_reached(self.condition_consecutive[rule_index])
                if force_clear:
                    active_alarm = None

            if active_alarm:
                # Still active, update dt_end & check if we have a new apex
                greatest_diff = self.greatest_rule_diff[rule_index]
                if diff:
                    if diff > greatest_diff:
                        self.greatest_rule_diff[rule_index] = diff
                        active_alarm.set_apex(val)
                self.__update_alarm(active_alarm, record.dt_recorded)
            else:
                # Not active, check if we should activate
                self.condition_consecutive[rule_index] += 1

                activate = self.__consecutive_ok(rule_index) and \
                    self.__duration_ok(rule_index, record) and \
                    self.__buffer_ok(rule_index, record) and \
                    self.__period_limit_ok(rule_index, record)

        if not passed or force_clear:
            # Clear
            self.condition_consecutive[rule_index] = 0
            self.condition_start_ts[rule_index] = None
            self.greatest_rule_diff[rule_index] = 0
            if active_alarm:
                deactivate = True
        return (activate, deactivate, val)

    def _run_processer(self, processer, records=None, run_ms=0):
        if records is None:
            records = []
        key_pattern = processer.get('analysis_key_pattern')
        if key_pattern:
            a = self._get_or_create_analysis(key_pattern)
            col = processer.get('column')
            expr = processer.get('expr', processer.get('calculation', None))
            if expr and col:
                ep = ExpressionParser(expr, col, analysis=a, run_ms=run_ms)
                res = ep.run(record_list=records, alarm_list=self.new_alarms)
                a.setColumnValue(col, res)


    def processRecord(self, record):
        # Listen for alarms
        # TODO: delays between two data points > NO DATA
        alarm = None
        for i, rule in enumerate(self.rules):
            activate, deactivate, value = self.__update_condition_status(i, record)
            if activate:
                alarm, alarm_processers = Alarm.Create(self.sensor, rule, record)
                alarm.put()
                if alarm_processers:
                    for processer in alarm_processers:
                        self._run_processer(processer, run_ms=tools.unixtime(alarm.dt_start))
                self.active_rules[i] = alarm
                self.recent_alarms[i].insert(0, alarm) # Prepend
            elif deactivate:
                ar = self.active_rules[i]
                if ar:
                    ar.deactivate()
                    self.active_rules[i] = None

        self.last_record = record
        return alarm

    def checkDeadline(self):
        TIMEOUT_SECS = 4*60 # 4 mins
        elapsed = tools.total_seconds(datetime.now() - self.start)
        logging.debug("%d / %d seconds elapsed..." % (elapsed, TIMEOUT_SECS))
        if elapsed >= TIMEOUT_SECS:
            raise TooLongError()

    def finish(self, result=PROCESS.OK, narrative=None):
        logging.debug("Finished...")
        # TODO: Should we set status OK even if no records processed?
        if self.last_record:
            self.sensorprocess.dt_last_record = self.last_record.dt_recorded
        if self.updated_alarm_dict:
            alarms = self.updated_alarm_dict.values()
            db.put(alarms)
        self.sensorprocess.dt_last_run = datetime.now()
        self.sensorprocess.status_last_run = result
        self.sensorprocess.narrative_last_run = narrative
        self.sensorprocess.put()
        logging.debug("Finished for %s. Last record: %s. Status: %s" % (self.sensorprocess, self.sensorprocess.dt_last_run, self.sensorprocess.print_status()))


    def run(self):
        self.start = datetime.now()
        self.setup()
        try:
            while True:
                batch = self.fetchBatch()
                if batch:
                    self.runBatch(batch)
                    self.checkDeadline()
                else:
                    self.finish()
                    break
        except (TooLongError, DeadlineExceededError):
            logging.debug("Deadline expired, creating new request...")
            tools.safe_add_task(self.run, _queue="worker-queue")
        except Exception, e:
            logging.exception("Uncaught error: %s" % e)
            self.finish(result=PROCESS.ERROR, narrative="Processing Error: %s" % e)

