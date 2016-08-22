import traceback
import tools
from constants import *
from models import *
from datetime import datetime
import logging
from expressionParser import ExpressionParser
from google.appengine.ext import db
from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import runtime
from errors import TooLongError, Shutdown

USE_DEFERRED = True



# TODO
# Rearchitect to query in window (last run to now (when worker starts))
# Otherwise we may miss records coming in during processing


class SensorProcessWorker(object):

    def __init__(self, sensorprocess, batch_size=50):
        self.sensorprocess = sensorprocess
        self.batch_size = batch_size
        self.cursor = None
        self.worker_start = datetime.now()
        self.start = self.worker_start
        self.sensor = sensorprocess.sensor
        self.ent = sensorprocess.enterprise
        self.process = sensorprocess.process
        self.dt_last_run = sensorprocess.dt_last_run
        self.dt_last_record = sensorprocess.dt_last_record
        self.query = self._get_query()
        self.processers = self.process.get_processers()  # JSON array of <processer>
        self.ep = None
        self.analyses = {}
        self.last_record = None
        self.sensorprocess.start(self.worker_start)
        self.sensorprocess.put()
        self.records_processed = 0
        self.continuations = 0


    def __str__(self):
        return "<SensorProcessWorker sensor_kn=%s from=%s to=%s />" % (self.sensor.key().name(), self._query_from(), self._query_until())

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

    def _query_from(self):
        return self.dt_last_record

    def _query_until(self):
        '''Define end of processing window as most recent record in db
            when worker starts.

        '''
        most_recent_record = self.sensor.record_set.order('-dt_recorded').get()
        if most_recent_record:
            return most_recent_record.dt_recorded
        else:
            return self.worker_start

    def _get_query(self):
        # Since time of last processed record
        # Until worker start.
        # TODO: Should end of range be query of most recent record recorded?
        # If future data comes in (within buffer), processing may be delayed
        # with current setup.
        _from = self._query_from()
        if not _from:
            logging.warning("Querying from beginning of time -- first run?")
        q = self.sensor.record_set \
            .filter('dt_recorded >', _from) \
            .filter('dt_recorded <=', self._query_until()) \
            .order('dt_recorded')
        return q

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
        '''Run processing on batch of records.

        Processing has two main steps:
            1) Processing each record and firing alarms if any of the tasks'
                rule conditions are met.
            2) For each processer defined, calculate the value as defined by
                the expressions, and update an analysis object with the specified
                key name.

        '''
        # Standard processing (alarms)
        logging.debug("---------Standard processing (alarms)-----------")
        self.new_alarms = []
        for record in records:
            new_alarm = self.processRecord(record)
            if new_alarm:
                self.new_alarms.append(new_alarm)

        # Analysis processing
        logging.debug("---------Analysis processing-------------------")
        if self.processers:
            for processer in self.processers:
                run_ms = tools.unixtime(records[-1].dt_recorded) if records else 0
                self._run_processer(processer, records=records, run_ms=run_ms)

        # TODO: Can we do this in finish?
        db.put(self.analyses.values())

        logging.debug("Ran batch of %d." % (len(records)))
        self.records_processed += len(records)

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
        '''Run expression-based processer with either:
            - Standard processing of a batch of records
            - Upon alarm creation if rule's processing spec is defined

        '''
        if records is None:
            records = []
        key_pattern = processer.get('analysis_key_pattern')
        if key_pattern:
            a = self._get_or_create_analysis(key_pattern)
            col = processer.get('column')
            expr = processer.get('expr', processer.get('calculation', None))
            if expr and col:
                # TODO: Slow?
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
        TIMEOUT_SECS = 4*60  # 4 mins
        elapsed = tools.total_seconds(datetime.now() - self.start)
        logging.debug("%d / %d seconds elapsed..." % (elapsed, TIMEOUT_SECS))
        if elapsed >= TIMEOUT_SECS:
            raise TooLongError()

    def finish(self, result=PROCESS.OK, narrative=None):
        if self.last_record and self.last_record.dt_recorded:
            self.sensorprocess.dt_last_record = self.last_record.dt_recorded
        if self.updated_alarm_dict:
            alarms = self.updated_alarm_dict.values()
            db.put(alarms)
        self.sensorprocess.finish(result, narrative)
        self.sensorprocess.put()
        logging.debug("FINISHED %s in %s seconds. %s records, %s continuations. Last record: %s. Status: %s" % (
            self.sensorprocess,
            self.sensorprocess.last_run_duration(),
            self.records_processed,
            self.continuations,
            self.sensorprocess.dt_last_run,
            self.sensorprocess.print_status()))

    def run(self):
        self.start = datetime.now()
        self.setup()
        logging.debug("Starting run %s" % self)
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
            logging.debug("Deadline expired, creating new request... Records: %s, Continuations: %s, Last record: %s" % (self.records_processed, self.continuations, self.last_record))
            self.continuations += 1
            task_name = self.sensorprocess.process_task_name(subset="cont_%s" % tools.unixtime())
            tools.safe_add_task(self.run, _name=task_name, _queue="processing-queue")
        except (Shutdown):
            logging.debug("Finishing because instance shutdown...")
            self.finish(result=PROCESS.ERROR, narrative="Instance shutdown")
        except Exception, e:
            logging.error("Uncaught error: %s" % e)
            traceback.print_exc()
            self.finish(result=PROCESS.ERROR, narrative="Processing Error: %s" % e)
