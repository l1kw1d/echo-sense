from constants import *
import json
import logging
from google.appengine.api import mail
from google.appengine.ext import deferred, db
from google.appengine.ext import webapp
import handlers
from models import *
from google.appengine.api import urlfetch


class DataParser(object):

    def __init__(self):
        pass

    def attemptParse(self, data):
        success = False
        message = None
        records = []
        try:
            records = self.parse(data)
            success = True
        except Exception, e:
            message = str(e)
        return (success, message, records)


class JSONDataParser(DataParser):
    """Parse incoming data in JSON format (list of Record objects)"""
    def __init__(self):
        super(JSONDataParser, self).__init__()

    def parse(self, data):
        records = json.loads(data)
        # Do any data standardization? Check for timestamp format etc? Sort?
        return records


class SMSSyncDataParser(DataParser):
    """Parse incoming message posted from SMSSync"""
    def __init__(self):
        super(SMSSyncDataParser, self).__init__()

    def parse(self, data):
        # TODO: Implement
        return []


class ParamsDataParser(DataParser):
    """Parse data as simple form POST"""
    def __init__(self):
        super(ParamsDataParser, self).__init__()

    def parse(self, data):
        records = []
        args = self.request.arguments()
        r = {
            'ts': self.request.get_range('ts')
        }
        for arg in args:
            r[arg] = self.request.get(arg)
        return records


class DataInbox(handlers.JsonRequestHandler):
    def post(self, eid, format, sensor_kn):
        success = False
        message = None
        data = {}
        eid = int(eid)
        error = 0
        logging.debug("1 - start of request handler")
        if sensor_kn:
            ekey = db.Key.from_path('Enterprise', eid)
            s = Sensor.get_by_key_name(sensor_kn, parent=ekey)
            if not s:
                default_sensortype_id = Enterprise.CachedDefaultSensorType(eid)
                if default_sensortype_id:
                    # Create on the fly only if we have a default sensortype
                    s = Sensor.Create(ekey, sensor_kn, default_sensortype_id)
            logging.debug("2 - after sensor fetch")
            if s:
                body = self.request.body
                records = None
                if format == 'json':
                    parser = JSONDataParser()
                    success, message, records = parser.attemptParse(body)
                    if success:
                        data['count'] = len(records)
                elif format == 'smssync':
                    parser = SMSSyncDataParser()
                    success, message, records = parser.attemptParse(body)
                    if success:
                        data['count'] = len(records)
                elif format == 'params':
                    # Standard form post params
                    parser = ParamsDataParser()
                    success, message, records = parser.attemptParse(body)
                    if success:
                        data['count'] = len(records)
                else:
                    logging.error("Unsupported format: %s" % format)
                logging.debug("3 - before saveRecords")
                n_records = s.saveRecords(records)
                if n_records:
                    s.dt_updated = datetime.now()
                    s.put()
                    if s.target:
                        s.target.dt_updated = s.dt_updated
                        s.target.put()
                    logging.debug("7 - after target put")
                    s.schedule_next_processing()
                    logging.debug("8 - after schedule next processing")
                    success = True
                else:
                    message = "No records saved"
            else:
                message = "Sensor not found and could not be created without a default type defined - %s" % sensor_kn
                error = ERROR.SENSOR_NOT_FOUND
        else:
            message = "Malformed - sensor key"
        self.json_out(data, success=success, message=message,
            error=error, debug=True)
