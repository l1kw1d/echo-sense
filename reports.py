import urllib, sys, os
import traceback
import tools
from models import *
from constants import *
from google.appengine.api import logservice
from google.appengine.runtime import DeadlineExceededError
import cloudstorage as gcs
import gc
import xlwt
import traceback
import csv
import json
from decorators import deferred_task_decorator

TEST_TOO_LONG_ON_EVERY_BATCH = False

class TooLongError(Exception):
    def __init__(self):
        pass

class GCSReportWorker(object):
    KIND = None
    FILTERS = []

    def __init__(self, rkey, start_att="__key__", start_att_direction=""):
        self.report = Report.get(rkey)

        if not self.report:
            logging.error("Error retrieving report [ %s ] from db" % rkey)
            return
        self.report.status = REPORT.GENERATING
        self.report.put()

        self.counters = {
            'run': 0,
            'skipped': 0
        }
        self.worker_start = tools.unixtime()
        self.cursor = None
        self.start_att = start_att
        self.start_att_direction = start_att_direction
        self.worker_cancelled = False
        self.prefetch_props = []
        self.date_columns = []
        self.headers = []
        self.date_att = None
        self.projection = None
        self.query = None
        self.batch_size = 300
        self.report_prog_mckey = MC_EXPORT_STATUS % self.report.key()
        self.setProgress({'val':0, "status":REPORT.GENERATING})
        self.gcs_file = gcs.open(self.getGCSFilename(), 'w')
        self.setup()

        # From: https://code.google.com/p/googleappengine/issues/detail?id=8809
        logservice.AUTOFLUSH_ENABLED = True
        logservice.AUTOFLUSH_EVERY_BYTES = None
        logservice.AUTOFLUSH_EVERY_SECONDS = 1
        logservice.AUTOFLUSH_EVERY_BYTES = 1024
        logservice.AUTOFLUSH_EVERY_LINES = 1

    def getGCSFilename(self, suffix="MAIN"):
        r = self.report
        filename = GCS_REPORT_BUCKET + "/eid_%d/%s.%s.%s" % (r.enterprise.key().id(), r.key(), suffix, r.extension)
        r.gcs_files.append(filename)
        return r.gcs_files[-1]

    def setup(self):
        if self.report.ftype == REPORT.XLS:
            font_h = xlwt.Font()
            font_h.bold = True
            style_h = xlwt.XFStyle()
            style_h.font = font_h

            self.xls_styles = {
                'datetime': xlwt.easyxf(num_format_str='D/M/YY h:mm'),
                'date': xlwt.easyxf(num_format_str='D/M/YY'),
                'time': xlwt.easyxf(num_format_str='h:mm'),
                'default': xlwt.Style.default_style,
                'bold': style_h
            }

            self.wb = xlwt.Workbook()
            self.ws = self.wb.add_sheet('Data')

    @deferred_task_decorator
    def run(self, start_cursor=None):
        self.worker_start = tools.unixtime()
        self.cursor = start_cursor
        self.setProgress({'max':self.count(), 'report': self.report.json()})

        if not start_cursor:
            self.writeHeaders()

        try:
            # This is heavy
            self.writeData()
        except TooLongError:
            logging.debug("TooLongError: Going to the next batch")
            if self.report:
                self.finish(reportDone=False)
                tools.safe_add_task(self.run, start_cursor=self._get_cursor(), _queue="report-queue")
        except Exception, e:  # including DeadlineExceededError
            traceback.print_exc()
            logging.error("Error: %s" % e)
            self.setProgress({'error': "Error occurred: %s" % e, 'status': REPORT.ERROR})
            return
        else:
            tools.safe_add_task(self.finish)

    def writeHeaders(self):
        if self.report.ftype == REPORT.CSV:
            string = tools.normalize_to_ascii('"'+'","'.join(self.headers)+'"\n')
            self.gcs_file.write(string)
            logging.debug(string)
        elif self.report.ftype == REPORT.XLS:
            for i, header in enumerate(self.headers):
                self.ws.write(0, i, header, self.xls_styles['bold'])

    def writeData(self):
        total_i = self.counters['run']
        while True:
            self.query = self._get_query()
            if self.query:
                entities = self.query.fetch(limit=self.batch_size)
                self.cursor = self._get_cursor()
                if not entities:
                    logging.debug("No rows returned by query -- done")
                    return
                else:
                    logging.debug("Got %d rows" % len(entities))
                if entities and self.prefetch_props:
                    entities = tools.prefetch_reference_properties(entities, *self.prefetch_props, missingRefNone=True)
                for entity in entities:
                    if entity:
                        ed = self.entityData(entity)
                    else:
                        continue
                    string = '?'
                    if self.report.ftype == REPORT.CSV:
                        csv.writer(self.gcs_file).writerow(tools.normalize_list_to_ascii(ed))
                    elif self.report.ftype == REPORT.XLS:
                        self.gcs_file.write(json.dumps(ed)+"\n")
                        if total_i > REPORT.XLS_ROW_LIMIT:
                            self.setProgress({'error': "XLS row limit (%d) exceeded!" % REPORT.XLS_ROW_LIMIT, 'status': REPORT.ERROR})
                            return
                    self.gcs_file.flush()

                    total_i += 1
                    self.counters['run'] += 1
                    if total_i % 100 == 0:
                        cancelled = self.updateProgressAndCheckIfCancelled()
                        if cancelled:
                            self.report.CleanDelete()
                            logging.debug("Worker cancelled by user, report deleted.")
                            return

                logging.debug("Batch of %d done" % len(entities))
                elapsed_ms = tools.unixtime() - self.worker_start
                elapsed = elapsed_ms / 1000
                if elapsed >= MAX_REQUEST_SECONDS or (tools.on_dev_server() and TEST_TOO_LONG_ON_EVERY_BATCH):
                    logging.debug("Elapsed %ss" % elapsed)
                    raise TooLongError()

            # self.setProgress() TODO: Implement background tasks via memcache

    def updateProgressAndCheckIfCancelled(self):
        progress = self.getProgress()
        return progress and progress.get('status') == REPORT.CANCELLED

    def getProgress(self):
        return memcache.get(self.report_prog_mckey)

    def setProgress(self, updatedProgress):
        progress = self.getProgress()
        if progress:
            progress.update(updatedProgress)
        else:
            progress = updatedProgress
        memcache.set(self.report_prog_mckey, progress)

    def entityData(self, entity):
        """
        Override with format specific to report type
        """
        self.setProgress({'val': 0})
        return []

    @deferred_task_decorator
    def finish(self, reportDone=True):
        """Called when the worker has finished, to allow for any final work to be done."""
        progress = None
        if reportDone:
            if self.report.ftype == REPORT.XLS:
                self.gcs_file.close()
                readable_gcs_file = gcs.open(self.gcs_file.name, 'r')
                data = readable_gcs_file.read().split("\n")
                readable_gcs_file.close()
                self.gcs_file = gcs.open(self.gcs_file.name, 'w')
                y = 0
                for r in data:
                    if not r:
                        continue
                    if y > REPORT.XLS_ROW_LIMIT:
                        logging.warning("Excel report exceeded row limit and was truncated")
                        break
                    y += 1
                    row = []
                    try:
                        row = json.loads(r)
                    except Exception, ex:
                        logging.error("Unable to json load row: %s (%s)" % (r, ex))
                    else:
                        for x, cell in enumerate(row):
                            if cell:
                                if x in self.report.date_columns:
                                    self.ws.write(y, x, cell, self.xls_styles['datetime'])
                                else:
                                    self.ws.write(y, x, cell)
                self.wb.save(self.gcs_file)

            self.gcs_file.close()
            self.report.status = REPORT.DONE
            self.report.dt_generated = datetime.now()
            self.report.put()
            duration = self.report.getDuration()
            logging.debug("GCSReportWorker finished. Counters: %s. Report ran for %d seconds." % (self.counters, duration))
            progress = {
                "status": REPORT.DONE,
                "resource":self.report.getGCSFile(),
                "generated": tools.unixtime(dt=self.report.dt_generated),
                "report": self.report.json(),
                "duration": duration
            }
        else:
            logging.debug("Batch finished. Counters: %s" % (self.counters))
        p = {
            'val':self.counters['run'],
            "filename":self.report.title
        }
        if progress:
            p.update(progress)
        self.setProgress(p)
        gc.collect() # Garbage collector

    def _get_cursor(self):
        return self.query.cursor() if self.query else None

    def _get_query(self):
        """Returns a query over the specified kind, with any appropriate filters applied."""
        if self.FILTERS:
            q = self.KIND.all()
            for prop, value in self.FILTERS:
                q.filter("%s" % prop, value)
            if self.start_att != "__key__":
                self.props = self.KIND.properties()
                if not self.props.has_key(self.start_att):
                    logging.error("Invalid Property %s for %s, not querying" % (self.start_att, self.KIND.kind()))
                    return None
            q.order("%s%s" % (self.start_att_direction, self.start_att))
            if self.cursor:
                q.with_cursor(self.cursor)
            return q
        else:
            logging.debug("No FILTERS, not querying")
            return None

    def count(self, limit=20000):
        q = self.KIND.all()
        for prop, value in self.FILTERS:
            q.filter("%s" % prop, value)
        if self.date_att and self.report.hasDateRange():
            q.order(self.date_att)
            if self.report.dateRange[0]: q.filter("%s >" % self.date_att, tools.ts_to_dt(self.report.dateRange[0]))
            if self.report.dateRange[1]: q.filter("%s <" % self.date_att, tools.ts_to_dt(self.report.dateRange[1]))
        return q.count(limit=limit)


class SensorDataReportWorker(GCSReportWorker):
    KIND = Record

    def __init__(self, sensorkey, rkey):
        super(SensorDataReportWorker, self).__init__(rkey, start_att="dt_recorded", start_att_direction="-")
        title_kwargs = {}
        specs = self.report.getSpecs()
        if sensorkey:
            self.sensor = Sensor.get(sensorkey)
            self.FILTERS = [("sensor =", self.sensor)]
            title_kwargs['sensor'] = str(self.sensor)
        elif specs.get('sensortype_id'):
            sensortype_id = specs.get('sensortype_id')
            title_kwargs['sensor_type'] = sensortype_id
            self.FILTERS = [("sensortype =", db.Key.from_path('SensorType', sensortype_id, parent=self.report.enterprise.key()))]
        else:
            # Enterprise wide
            self.FILTERS = [("enterprise =", self.report.enterprise)]
        start = specs.get("start", 0)
        end = specs.get("end", 0)
        if start:
            self.FILTERS.append(("dt_recorded >=", tools.dt_from_ts(start)))
        if end:
            self.FILTERS.append(("dt_recorded <", tools.dt_from_ts(end)))
        self.report.generate_title("Sensor Data Report", ts_start=start, ts_end=end, **title_kwargs)
        self.columns = specs.get('columns', [])
        standard_cols = ["Sensor ID", "Date"]
        self.headers = standard_cols + self.columns
        self.batch_size = 1000

    def entityData(self, rec):
        row = [
            "ID:%s" % tools.getKey(Record, 'sensor', rec, asID=True),
            tools.sdatetime(rec.dt_recorded, fmt="%Y-%m-%d %H:%M:%S %Z")
        ]
        for col in self.columns:
            row.append(str(rec.columnValue(col, default="")))
        return row

class AlarmReportWorker(GCSReportWorker):
    KIND = Alarm

    def __init__(self, entkey, rkey):
        super(AlarmReportWorker, self).__init__(rkey, start_att="dt_start", start_att_direction="-")
        self.enterprise = self.report.enterprise
        self.FILTERS = [("enterprise =", self.enterprise)]
        specs = self.report.getSpecs()
        start = specs.get("start", 0)
        end = specs.get("end", 0)
        if start:
            self.FILTERS.append(("dt_start >=", tools.dt_from_ts(start)))
        if end:
            self.FILTERS.append(("dt_start <", tools.dt_from_ts(end)))
        self.report.generate_title("Alarm Report", ts_start=start, ts_end=end)
        self.sensor_lookup = tools.lookupDict(Sensor, self.enterprise.sensor_set.fetch(limit=200), valueTransform=lambda s : s.name)
        self.rule_lookup = tools.lookupDict(Rule, self.enterprise.rule_set.fetch(limit=100))
        self.headers = ["Sensor ID","Sensor","Rule","Apex","Start","End"]

    def entityData(self, alarm):
        sensor_id = tools.getKey(Alarm, 'sensor', alarm, asID=False)
        sensor_name = self.sensor_lookup.get(sensor_id, "")
        rule_name = str(self.rule_lookup.get(tools.getKey(Alarm, 'rule', alarm, asID=False), ""))
        apex = "%.2f" % alarm.apex if alarm.apex is not None else "--"
        row = ["ID:%s" % sensor_id, sensor_name, rule_name, apex, tools.sdatetime(alarm.dt_start), tools.sdatetime(alarm.dt_end)]
        return row

class APILogReportWorker(GCSReportWorker):
    KIND = APILog

    def __init__(self, rkey):
        super(APILogReportWorker, self).__init__(rkey, start_att="date", start_att_direction="-")
        self.enterprise = self.report.enterprise
        self.FILTERS = [("enterprise =", self.enterprise)]
        specs = self.report.getSpecs()
        start = specs.get("start", 0)
        end = specs.get("end", 0)
        if start:
            self.FILTERS.append(("date >=", tools.dt_from_ts(start)))
        if end:
            self.FILTERS.append(("date <", tools.dt_from_ts(end)))
        self.report.generate_title("API Log Report", ts_start=start, ts_end=end)
        self.headers = ["User ID","Date","Path","Method","Request"]

    def entityData(self, apilog):
        uid = "ID:%s" % tools.getKey(APILog, 'user', apilog, asID=True)
        row = [uid, tools.sdatetime(apilog.date), apilog.path, apilog.method, apilog.request]
        return row


class AnalysisReportWorker(GCSReportWorker):
    KIND = Analysis

    def __init__(self, entkey, rkey):
        super(AnalysisReportWorker, self).__init__(rkey, start_att="dt_created", start_att_direction="-")
        self.enterprise = self.report.enterprise
        self.FILTERS = [("enterprise =", self.enterprise)]
        specs = self.report.getSpecs()
        start = specs.get("start", 0)
        end = specs.get("end", 0)
        self.columns = specs.get("columns", "").split(",")
        sensortype_id = specs.get("sensortype_id")
        self.report.generate_title("Analysis Report", ts_start=start, ts_end=end, sensortype_id=sensortype_id)
        if start:
            self.FILTERS.append(("dt_created >=", tools.dt_from_ts(start)))
        if end:
            self.FILTERS.append(("dt_created <", tools.dt_from_ts(end)))
        if sensortype_id:
            self.FILTERS.append(("sensortype =", db.Key.from_path('Enterprise', self.enterprise.key().id(), 'SensorType', int(sensortype_id))))
        self.sensor_lookup = tools.lookupDict(Sensor, self.enterprise.sensor_set.fetch(limit=200), valueTransform=lambda s : s.name)
        self.headers = ["Key","Sensor","Created","Updated"] + self.columns


    def entityData(self, analysis):
        sensor_name = self.sensor_lookup.get(tools.getKey(Analysis, 'sensor', analysis, asID=False), "")
        row = [analysis.key().name(), sensor_name, tools.sdatetime(analysis.dt_created), tools.sdatetime(analysis.dt_updated)]
        for col in self.columns:
            value = analysis.columnValue(col, default="")
            row.append(value)
        return row
