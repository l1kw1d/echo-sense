import logging
from datetime import datetime, timedelta

from google.appengine.api import mail, memcache, taskqueue
from google.appengine.ext import deferred, db
from models import Report
from constants import *

import handlers


# class ScheduleFirstProcessTask(handlers.BaseRequestHandler):
#     def get(self):
#         # Loop through all processtasks and schedule first run for tomorrow
#         # Each task will complete and then fire off next task (after interval)
#         now = datetime.now()
#         tasks = ProcessTask.all().fetch(limit=None)
#         logging.info("Running ScheduleFirstProcessTask for %d tasks" % len(tasks))
#         for task in tasks:
#             if task.runs_today(day_offset=1):  # Tomorrow
#                 # TODO: Check if we have any sensorprocesses linked?
#                 tomorrow = now + timedelta(days=1)
#                 eta = datetime.combine(tomorrow.date(), task.time_start)
#                 logging.info("Scheduling task for %s UTC" % eta)
#                 tools.safe_add_task("/tasks/processtask/run", params={'key':str(task.key())}, eta=eta)
#             else:
#                 logging.debug("%s doesn't run tomorrow" % task)


class WarmupHandler(handlers.BaseRequestHandler):
    def get(self):
        logging.info("Warmup Request")


class Monthly(handlers.BaseRequestHandler):
    def get(self):
        # Delete reports older than 1 month
        cutoff = datetime.now() - timedelta(days=30)
        reports_to_delete = Report.all().filter("dt_created <", cutoff).fetch(limit=50)
        for r in reports_to_delete:
            r.CleanDelete(self_delete=False)
        n = len(reports_to_delete)
        db.delete(reports_to_delete)
        logging.debug("Deleting %d reports created before %s" % (n, cutoff))


class Weekly(handlers.BaseRequestHandler):
    def get(self):
        pass


class AdminDigest(handlers.BaseRequestHandler):
    def get(self):
        pass
