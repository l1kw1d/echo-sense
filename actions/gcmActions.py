import os, logging
from datetime import datetime,timedelta

from google.appengine.ext import db
from google.appengine.api import images, taskqueue
import logging
from models import *
import tools
import services
import authorized

import json

import handlers

class GCMConnection(handlers.JsonRequestHandler):
    @authorized.role('api')
    def post(self, d):
        success = False
        message = None
        regid = self.request.get('regid')
        if d['user'] and regid:
            logging.debug("Got new gcm registration id: %s" % regid)
            d['user'].Update(gcm_reg_id=regid)
            d['user'].put()
            success = True
        else:
            message = "User not found or no regid"
        self.json_out(success=success, message=message, data={"reg_id": regid})
