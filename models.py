import logging
from datetime import datetime, timedelta
import webapp2
from google.appengine.ext import db, deferred, blobstore
from google.appengine.api import memcache, mail, images, taskqueue, search
import json
import services
import outbox
from markupsafe import Markup
from constants import *
from decorators import auto_cache
from expressionParser import ExpressionParser
import tools
from user_defined_props import DecimalProperty


class UserAccessible(db.Model):
    '''
    Parent class for items that have gated user access (e.g. sensor, entity)
    Also enables full-text-search functionality
    '''

    FTS_DOC_NAME = "label"

    @classmethod
    def GetAccessible(cls, key_or_id, acc, parent=None):
        if key_or_id:
            if type(key_or_id) in [int, long] or (type(key_or_id) in [str, unicode] and key_or_id.isdigit()):
                key = db.Key.from_path(cls.__name__, int(key_or_id), parent=parent.key() if parent else None)
            else:
                key = db.Key(key_or_id)
            item = db.get(key)
            if item:
                if item.accessible(acc):
                    return item
            else:
                logging.debug("%s not found" % (key_or_id))
        return None

    def accessible(self, acc):
        entkey = self.getEnterprise(key=True)
        acc_entkey = tools.getKey(None, 'enterprise', acc, asID=False)
        is_accessible = entkey == acc_entkey
        if not is_accessible:
            logging.debug("%s not accessible by %s" % (self, acc))
        return is_accessible

    def getEnterprise(self, key=False):
        '''
        Inheriting models should override if prop is named something else
        '''
        if key:
            return tools.getKey(None, 'enterprise', self, asID=False)
        else:
            return self.enterprise

    def get_doc_id(self):
        '''Override'''
        return None

    def get_searchable_type(self):
        '''Override'''
        return None

    def get_searchable_label(self):
        '''Override'''
        return None

    def get_searchable_index(self):
        eid = tools.getKey(None, 'enterprise', self, asID=True)
        return search.Index(name=FTS_INDEX % eid)

    def full_doc_id(self):
        doc_id = self.get_searchable_type() + ":" + str(self.get_doc_id())
        return doc_id

    def generate_search_doc(self):
        doc_id = self.full_doc_id()
        fields = [
            search.TextField(name=self.FTS_DOC_NAME, value=self.get_searchable_label())
        ]
        sd = search.Document(doc_id=doc_id, fields=fields, language='en')
        return sd

    def updateSearchDoc(self, delete=False):
        index = self.get_searchable_index()
        try:
            doc_id = self.full_doc_id()
            if doc_id:
                if delete:
                    index.delete([doc_id])
                else:
                    sd = self.generate_search_doc()
                    index.put(sd)
        except search.Error, e:
            logging.debug("Search Index Error when updating search doc: %s" % e)


class Enterprise(db.Model):
    """
    Key - ID
    """
    name = db.StringProperty()
    dt_created = db.DateTimeProperty(auto_now_add=True)
    country = db.StringProperty(default= "KE") # Alpha 2
    timezone = db.StringProperty(indexed=False, default="UTC")
    alias = db.StringProperty()
    gateway_config = db.TextProperty() # JSON
    default_sensortype = db.IntegerProperty(indexed=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Enterprise id=%s>" % self.key().id()

    def json(self):
        return {
            'key': str(self.key()),
            'id': self.key().id(),
            'name': self.name,
            'country': self.country,
            'timezone': self.timezone,
            'alias': self.alias,
            'default_sensortype': self.default_sensortype,
            'gateway_config': self.gateway_config
        }

    @staticmethod
    def standard_alias(alias):
        return tools.lower_no_spaces(alias)

    @staticmethod
    def Create():
        return Enterprise()

    @staticmethod
    def Get(alias=None):
        e = None
        if alias:
            alias = Enterprise.standard_alias(alias)
            e = Enterprise.all().filter("alias =",alias).get()
        return e

    def Update(self, **params):
        if 'name' in params:
            self.name = params['name']
        if 'country' in params:
            self.country = params['country']
        if 'timezone' in params:
            self.timezone = params['timezone']
        if 'alias' in params:
            if params['alias']:
                self.alias = Enterprise.standard_alias(params['alias'])
        if 'default_sensortype' in params and params.get('default_sensortype'):
            self.default_sensortype = int(params['default_sensortype'])
        if 'gateway_config' in params:
            self.gateway_config = json.dumps(params['gateway_config'])

    def get_timezone(self):
        return self.timezone

    def get_gateway_property(self, gateway_id=None, prop='apikey'):
        config = tools.getJson(self.gateway_config)
        if config and gateway_id in config:
            return config[gateway_id].get(prop)
        return None

    def get_search_index(self):
        return search.Index(name=FTS_INDEX % self.key().id())

    def get_default_sensortype(self):
        st_id = None
        if self.default_sensortype:
            st_id = self.default_sensortype
        return st_id

    @staticmethod
    @auto_cache()
    def CachedDefaultSensorType(eid):
        e = Enterprise.get_by_id(eid)
        if e:
            return e.get_default_sensortype()
        return None

class User(db.Model):
    """
    Key - ID
    """
    enterprise = db.ReferenceProperty(Enterprise)
    pw_sha = db.StringProperty(indexed=False)
    pw_salt = db.StringProperty(indexed=False)
    name = db.StringProperty(indexed=False)
    email = db.StringProperty()
    phone = db.StringProperty()  # Standard international
    gcm_reg_id = db.TextProperty() # Google Cloud Messaging
    dt_created = db.DateTimeProperty(auto_now_add=True)
    dt_last_login = db.DateTimeProperty(auto_now_add=True)
    level = db.IntegerProperty(default=USER.LIMITED_READ_WRITE)
    group_ids = db.ListProperty(int, default=[])  # IDs of SensorGroup()s user can access
    location_text = db.StringProperty(indexed=False)
    alert_channel = db.IntegerProperty(default=0) # CHANNEL() or 0 for disabled
    custom_attrs = db.TextProperty() # JSON attributes
    currency = db.TextProperty(default="USD") # 3-letter e.g. USD
    # Avatar
    av_data_key = db.StringProperty(indexed=False) # GCS file
    av_storage = db.IntegerProperty(default=MEDIA.GCS)
    av_content_type = db.StringProperty(indexed=False)

    def __str__(self):
        return self.name if self.name else "User"

    def json(self, custom_attrs=None):
        if custom_attrs is None:
            custom_attrs = []
        data = {
            'id': self.key().id(),
            'enterprise_id': tools.getKey(User, 'enterprise', self, asID=True),
            'level':self.level,
            'level_name':self.print_level(),
            'name': self.name,
            'email':self.email,
            'phone': self.phone,
            'currency': self.currency,
            'location_text': self.location_text,
            'ts_created': tools.unixtime(self.dt_created),
            'group_ids': self.group_ids,
            'gcm_reg_id': self.gcm_reg_id,
            'alert_channel': self.alert_channel,
            'avatar_serving_url': self.avatar_serving_url(size=500)
        }
        if custom_attrs:
            attr_dict = self.get_custom_attributes()
            for attr in custom_attrs:
                data[attr] = attr_dict.get(attr, "")
        else:
            data['custom_attrs'] = self.custom_attrs # Raw JSON string
        if self.enterprise:
            data.update({
                'ent_name': self.enterprise.name,
                'ent_id': self.enterprise.key().id(),
                'timezone': self.enterprise.timezone,
                'country': self.enterprise.country
                })
        return data

    @staticmethod
    def FuzzyGet(login):
        is_email = tools.is_valid_email(login)
        if is_email:
            return User.GetByEmail(login)
        else:
            phone = tools.standardize_phone(login)
            if phone:
                return User.GetByPhone(phone)
        return None


    @staticmethod
    def GetByEmail(email):
        u = User.all().filter("email =",email.lower()).get()
        return u

    @staticmethod
    def GetByPhone(phone):
        u = User.all().filter("phone =",tools.standardize_phone(phone)).get()
        return u

    @staticmethod
    def GetByGoogleId(id):
        u = User.all().filter("g_id =",id).get()
        return u

    @staticmethod
    def Create(enterprise, email=None, phone=None, level=None, notify=True):
        if enterprise and (email or phone):
            u = User(enterprise=enterprise, email=email.lower() if email else None, phone=tools.standardize_phone(phone))
            if email and email.lower() == ADMIN_EMAIL:
                u.level = USER.ADMIN
            elif notify:
                deferred.defer(mail.send_mail, SENDER_EMAIL, NOTIF_EMAILS, EMAIL_PREFIX + " New User: %s" % email, "That is all")
            return u
        return None

    @staticmethod
    def UsersFromSensorContactIDs(sensor, contact_id_list):
        contact_dict = sensor.get_contacts()
        uids = []
        if contact_dict:
            for contact_id in contact_id_list:
                if contact_id in contact_dict:
                    user = None
                    uid = contact_dict.get(contact_id, None)
                    if uid:
                        uids.append(uid)
        users = User.get_by_id(uids)
        return [u for u in users if u] # Filter nones


    def Update(self, **params):
        if 'name' in params:
            self.name = params['name']
        if 'email' in params:
            self.email = params['email']
        if 'phone' in params:
            self.phone = params['phone']
        if 'level' in params:
            self.level = params['level']
        if 'location_text' in params:
            self.location_text = params['location_text']
        if 'password' in params:
            if params['password']:
                self.setPass(params['password'])
        if 'group_ids' in params:
            self.group_ids = [int(gid) for gid in params['group_ids']]
        if 'alert_channel' in params:
            self.alert_channel = int(params['alert_channel'])
        if 'av_data_key' in params:
            self.av_data_key = params['av_data_key']
        if 'av_content_type' in params:
            self.av_content_type = params['av_content_type']
        if 'gcm_reg_id' in params:
            self.gcm_reg_id = params['gcm_reg_id']
        if 'custom_attrs' in params:
            self.custom_attrs = json.dumps(params['custom_attrs'])
        if 'currency' in params:
            self.currency = params['currency']


    def print_level(self):
        return USER.LABELS.get(self.level)

    def is_admin(self):
        return self.level == USER.ADMIN

    def is_account_admin(self):
        return self.level == USER.ACCOUNT_ADMIN

    def clean_delete(self):
        self.delete()

    def getTimezone(self):
        if self.timezone:
            return pytz.timezone(self.timezone)
        return self.enterprise.get_timezone()

    def validatePassword(self, user_password):
        salt, pw_sha = tools.getSHA(user_password, self.pw_salt)
        pw_valid = self.pw_sha == pw_sha
        return pw_valid

    def setPass(self, pw=None):
        if not pw:
            pw = tools.GenPasswd(length=6)
        self.pw_salt, self.pw_sha = tools.getSHA(pw)
        return pw

    @staticmethod
    def ValidateLogin(user, password):
        pw_valid = False
        login_attempts = None
        if user and password:
            pw_valid, login_attempts = user.validatePassword(password)
        return pw_valid, login_attempts

    def avatar_serving_url(self, size=500):
        if self.av_data_key:
            gskey = blobstore.create_gs_key(filename=self.av_data_key)
            return images.get_serving_url(gskey, size=size)
        else:
            return "/images/user.png"

    def has_avatar(self):
        return self.av_data_key is not None

    def get_custom_attributes(self):
        atts = tools.getJson(self.custom_attrs)
        if not atts:
            atts = {}
        return atts

    def get_groups(self):
        if self.group_ids:
            return [sg for sg in SensorGroup.get_by_id(self.group_ids) if sg]
        else:
            return []

class Target(UserAccessible):
    '''
    Parent - Enterprise
    Key - ID
    Target asset or location that is being measured by one or more sensors
    '''
    dt_created = db.DateTimeProperty(auto_now_add=True)
    dt_updated = db.DateTimeProperty(auto_now_add=True)  # Last received data (not date of data)
    name = db.StringProperty()
    group_ids = db.ListProperty(int, default=[])  # IDs of groups
    enterprise = db.ReferenceProperty(Enterprise)
    location = db.GeoPtProperty()
    color = db.StringProperty(indexed=False)
    size = db.IntegerProperty(indexed=False)
    bearing = db.IntegerProperty(indexed=False) # Degrees CCW (0 = North)

    def __repr__(self):
        return "<Target name=%s>" % self.name


    def json(self):
        res = {
            'key': str(self.key()),
            'id': self.key().id(),
            'name': self.name,
            'group_ids': self.group_ids,
            'location': str(self.location) if self.location else None,
            'color': self.color,
            'size': self.size,
            'bearing': self.bearing,
            'ts_created': tools.unixtime(self.dt_created),
            'ts_updated': tools.unixtime(self.dt_updated)
        }
        if self.location:
            res['lat'] = self.location.lat
            res['lon'] = self.location.lon
        return res


    @staticmethod
    def Create(e):
        return Target(parent=e, enterprise=e)

    def Update(self, **params):
        if 'name' in params:
            self.name = params['name']
        if 'group_ids' in params:
            self.group_ids = [int(x) for x in params['group_ids'] if x is not None]
        if 'lat' in params and 'lon' in params:
            lat = params['lat']
            lon = params['lon']
            if lat and lon:
                self.location = db.GeoPt("%s,%s" % (params['lat'],params['lon']))
            else:
                self.location = None

    def update_state(self, role, val):
        if role == COLUMN.LOCATION:
            gp = db.GeoPt(val)
            if gp.lat or gp.lon:
                logging.debug("Updating location: %s" % val)
                self.location = gp
        elif role == COLUMN.COLOR:
            # TODO: Implement - set color based on val/min/max
            pass
        elif role == COLUMN.SIZE:
            # TODO: Implement
            pass
        elif role == COLUMN.BEARING:
            if int(val) in range(360):
                self.bearing = int(val)

    def can_delete(self):
        any_linked_sensor = self.sensor_set.get() is not None
        return not any_linked_sensor

    def clean_delete(self, **params):
        message = None
        success = False
        if self.can_delete():
            self.updateSearchDoc(delete=True)
            self.delete()
            success = True
        else:
            message = "One or more linked sensors, cannot delete target"
        return (success, message)

    # FTS overrides

    def get_doc_id(self):
        return self.key().id()

    def get_searchable_type(self):
        return 'target'

    def get_searchable_label(self):
        '''Override'''
        return self.name

    @staticmethod
    def Fetch(user, updated_since=None, group_id=None, limit=50):
        e = user.enterprise
        q = Target.all().ancestor(e)
        if updated_since:
            q.filter("dt_updated >", updated_since)
        elif group_id:
            q.filter("group_ids =", group_id)
        targets = q.fetch(limit=limit)
        if user.is_admin() or user.is_account_admin():
            # Fetch all targets in ent
            return targets
        else:
            # Otherwise filter to targets in same group as user
            return filter(lambda trg : any([id in trg.group_ids for id in user.group_ids]), targets)


class SensorGroup(UserAccessible):
    '''
    Parent - Enterprise
    Key - ID
    '''
    # TODO: Are 'tags' a clearer concept?
    name = db.StringProperty()
    enterprise = db.ReferenceProperty(Enterprise)
    dt_created = db.DateTimeProperty(auto_now_add=True)

    def __repr__(self):
        return "<SensorGroup name=%s>" % self.name

    def json(self):
        return {
            'key': str(self.key()),
            'id': self.key().id(),
            'name': self.name,
            'ts_created': tools.unixtime(self.dt_created)
        }

    @staticmethod
    def Create(e):
        return SensorGroup(parent=e, enterprise=e)

    def Update(self, **params):
        if 'name' in params:
            self.name = params['name']

    def can_delete(self):
        any_linked_sensor = Sensor.all().filter("group_ids =", self.key().id()).get() is not None
        any_linked_target = Target.all().filter("group_ids =", self.key().id()).get() is not None
        return not any([any_linked_sensor, any_linked_target])

    def clean_delete(self):
        if self.can_delete():
            self.delete()
            return True
        return False

    # FTS overrides

    def get_doc_id(self):
        return self.key().id()

    def get_searchable_type(self):
        return 'group'

    def get_searchable_label(self):
        '''Override'''
        return self.name

class SensorType(UserAccessible):
    """
    Parent - Enterprise
    Key - ID
    Defines a class of sensor, with schema of data collected

    schema - object, keys = column, values = object:
    * 'label' - label
    * 'unit' - e.g. kph
    * 'role' - int list, see COLUMN roles
    * 'type' - E.g. 'number' or 'latlng'. See Google Visualization data types
    * 'calculation' - Expression parsed by expressionParser
    Schema can include both raw props and calculated/processed props that can be populated
    during processing or upon post
    """
    enterprise = db.ReferenceProperty(Enterprise, required=True)
    dt_created = db.DateTimeProperty(auto_now_add=True)
    name = db.StringProperty(indexed=False)
    alias = db.StringProperty() # Lower, no spaces
    schema = db.TextProperty() # Json

    def __repr__(self):
        return "<SensorType>"


    def json(self):
        return {
            'key': str(self.key()),
            'id': self.key().id(),
            'enterprise_id': tools.getKey(SensorType, 'enterprise', self, asID=True),
            'name': self.name,
            'alias': self.alias,
            'ts_created': tools.unixtime(self.dt_created),
            'schema': self.schema
        }

    def get_schema(self):
        j = tools.getJson(self.schema)
        if j is None:
            j = {}
        return j

    @staticmethod
    def Create(e):
        return SensorType(parent=e, enterprise=e)

    def Update(self, **params):
        if 'name' in params:
            self.name = params['name']
        if 'alias' in params:
            self.alias = tools.lower_no_spaces(params['alias'])
        if 'schema' in params:
            self.schema = json.dumps(params['schema'])

    def clean_delete(self):
        if self.sensor_set.count(limit=1):
            return False
        else:
            db.delete(self.sensor_set)
            self.delete()
            return True

    @staticmethod
    def Get(e, alias):
        return e.sensortype_set.filter("alias =", alias).get()

    @staticmethod
    def Fetch(e, limit=50):
        return SensorType.all().ancestor(e).fetch(limit=limit)

class Sensor(UserAccessible):
    """
    Parent - Enterprise
    Key - Name
    """
    name = db.StringProperty(default="Unknown Sensor")
    sensortype = db.ReferenceProperty(SensorType)
    target = db.ReferenceProperty(Target)
    enterprise = db.ReferenceProperty(Enterprise, required=True)
    dt_created = db.DateTimeProperty(auto_now_add=True)
    dt_updated = db.DateTimeProperty(auto_now_add=True)  # Last received data (not date of data)
    contacts = db.TextProperty(indexed=False)  # JSON contact alias (e.g. 'driver') -> uid
    group_ids = db.ListProperty(int, default=[])  # IDs of groups
    # State - Standard representation mapping of latest state (mapped from roles of most recent datapoint)
    # TODO: Should we move state to Target()?
    location = db.GeoPtProperty()
    # color = db.StringProperty(indexed=False)
    # size = db.IntegerProperty(indexed=False)
    bearing = db.IntegerProperty(indexed=False) # Degrees CCW (0 = North), Deprecate

    def __repr__(self):
        return "<Sensor name=%s kn=%s>" % (self.name, self.key().name())

    def __str__(self):
        return self.name if self.name else "Sensor"

    def json(self, with_records=0, with_alarms=0, with_analyses=0, record_downsample=DOWNSAMPLE.NONE, rule_id_filter=None, with_processers=False, with_sensortype=False):
        res = {
            'key': str(self.key()),
            'kn': self.key().name(),
            'name': self.name,
            'ts_created': tools.unixtime(self.dt_created),
            'ts_updated': tools.unixtime(self.dt_updated),
            'sensortype_id': tools.getKey(Sensor, 'sensortype', self, asID=True),
            'enterprise_id': tools.getKey(Sensor, 'enterprise', self, asID=True),
            'target_id': tools.getKey(Sensor, 'target', self, asID=True),
            'contacts': self.contacts,
            'group_ids': self.group_ids,
            'location': str(self.location) if self.location else None,
            'bearing': self.bearing
        }
        if with_sensortype and self.sensortype:
            # Note: prefetch props if fetching list
            res['sensortype'] = self.sensortype.json()
        if self.location:
            res['lat'] = self.location.lat
            res['lon'] = self.location.lon
        if with_records:
            records = Record.Fetch(self, downsample=record_downsample, limit=with_records)
            res['records'] = [r.json() for r in records]
        if with_alarms:
            rule = None
            if rule_id_filter:
                rule = db.Key.from_path('Rule', rule_id_filter, parent=tools.getKey(Sensor, 'enterprise', self, asID=False, keyObj=True))
            alarms = Alarm.Fetch(sensor=self, rule=rule, limit=with_alarms)
            res['alarms'] = [a.json() for a in alarms]
        if with_analyses:
            analyses = Analysis.Fetch(self, limit=with_analyses)
            res['analyses'] = [a.json() for a in analyses]
        if with_processers:
            # Note: this defaults to autofetch
            res['processers'] = [spt.json() for spt in SensorProcessTask.Fetch(self, refresh=True)]
        return res

    @staticmethod
    def Fetch(user, updated_since=None, target_id=None, group_id=None, limit=50, offset=0):
        e = user.enterprise
        q = Sensor.all().ancestor(e)
        if updated_since:
            q.filter("dt_updated >", updated_since)
        elif target_id:
            q.filter("target =", db.Key.from_path('Target', target_id, parent=e.key()))
        elif group_id:
            q.filter("group_ids =", group_id)
        sensors = q.fetch(limit=limit, offset=offset)
        if user.is_admin() or user.is_account_admin():
            # Fetch all sensors in ent
            return sensors
        else:
            # Otherwise filter to sensors in same group as user
            return filter(lambda s : any([id in s.group_ids for id in user.group_ids]), sensors)

    @staticmethod
    def Create(e, kn, sensortype_id):
        sensortype = db.Key.from_path('SensorType', sensortype_id, parent=e.key())
        return Sensor(key_name=kn, parent=e, enterprise=e, sensortype=sensortype)


    def schedule_next_processing(self):
        """Schedule process tasks in a batched manner.

        Usually called after receiving data.

        """
        spts = SensorProcessTask.Fetch(sensor=self)
        for spt in spts:
            spt.schedule_run()


    # TODO: Deprecate
    def update_state(self, role, val):
        if role == COLUMN.LOCATION:
            gp = db.GeoPt(val)
            if gp.lat or gp.lon:
                logging.debug("Updating location: %s" % val)
                self.location = gp
        elif role == COLUMN.BEARING:
            if int(val) in range(360):
                self.bearing = int(val)

    def Update(self, **params):
        if 'name' in params:
            self.name = params['name']
        if 'sensortype_id' in params:
            if params['sensortype_id']:
                self.sensortype = db.Key.from_path('SensorType', params['sensortype_id'], parent=tools.getKey(Sensor, 'enterprise', self, asID=False, keyObj=True))
            else:
                self.sensortype = None
        if 'contacts' in params:
            self.contacts = json.dumps(params['contacts'])
        if 'lat' in params and 'lon' in params:
            lat = params['lat']
            lon = params['lon']
            if lat and lon:
                self.location = db.GeoPt("%s,%s" % (params['lat'],params['lon']))
            else:
                self.location = None
        if 'group_ids' in params:
            self.group_ids = [int(gid) for gid in params['group_ids']]
        if 'target_id' in params:
            if params['target_id']:
                self.target = db.Key.from_path('Target', params['target_id'], parent=tools.getKey(Sensor, 'enterprise', self, asID=False, keyObj=True))
            else:
                self.target = None

    def saveRecords(self, records):
        '''
        Takes records as list of dicts and saves to datastore
        Dicts must contain a value for 'timestamp' as well as at least one
        dynamic property as defined by sensortype schema
        '''
        put_records = []
        now_ts = tools.unixtime()
        if records:
            if 'timestamp' not in records[0]:
                logging.warning("Record missing 'timestamp'")
            else:
                if self.sensortype:
                    schema = self.sensortype.get_schema()
                    if schema:
                        expression_parser_by_col = {}
                        for column, colschema in schema.items():
                            if 'calculation' in colschema:
                                calc = colschema.get('calculation')
                                if calc:
                                    expression_parser_by_col[column] = ExpressionParser(calc, column)
                                    continue
                        # Sort with newest records last
                        for i, r in enumerate(sorted(records, key=lambda r : r.get('timestamp'))):
                            ts = int(r.get('timestamp'))
                            if ts:
                                last = i == len(records) - 1
                                try:
                                    _r = Record.Create(ts, self, r, apply_roles=last, schema=schema, expression_parser_by_col=expression_parser_by_col)
                                except Exception, e:
                                    logging.error("Error creating record: %s" % e)
                                    _r = None
                                if _r:
                                    put_records.append(_r)
                        db.put(put_records)
                else:
                    logging.warning("Can't save records - no type for %s" % self)
        return len(put_records)

    def get_contacts(self):
        return tools.getJson(self.contacts)

    def clean_delete(self):
        can_delete = self.record_set.count(limit=101) < 100
        if can_delete:
            db.delete(self.alarm_set.fetch(limit=None))
            db.delete(self.record_set.fetch(limit=None))
            db.delete(self.analysis_set.fetch(limit=None))
            db.delete(self.sensorprocesstask_set.fetch(limit=None))
            self.updateSearchDoc(delete=True)
            self.delete()
            return True
        return False

    # FTS overrides

    def get_doc_id(self):
        return self.key().name()

    def get_searchable_type(self):
        return 'sensor'

    def get_searchable_label(self):
        return self.name

class Rule(db.Model):
    """
    Parent - Enterprise
    Key - ID
    Spec of alarm, e.g. speeding, over-heating
    Can optionally include alerts to send (recipients defined by sensor)
    or payments to make
    """
    name = db.StringProperty()
    enterprise = db.ReferenceProperty(Enterprise)
    dt_created = db.DateTimeProperty(auto_now_add=True)
    # Parameters
    column = db.StringProperty(indexed=False)  # Dyanmic prop name
    # Activation params
    trigger = db.IntegerProperty(indexed=False)
    duration = db.IntegerProperty(default=0, indexed=False) # ms
    consecutive = db.IntegerProperty(default=RULE.DISABLED, indexed=False)
    plimit_type = db.IntegerProperty(default=RULE.DISABLED, indexed=False) # Period limit (type)
    plimit = db.IntegerProperty(default=0, indexed=False) # Period limit (limit alarms per period)
    # Deactivation params
    consecutive_limit = db.IntegerProperty(default=RULE.DISABLED, indexed=False)
    buffer = db.IntegerProperty(default=0)  # ms within which new alarm can't be raised
    value1 = db.FloatProperty(indexed=False)
    value2 = db.FloatProperty(indexed=False)
    value_complex = db.TextProperty() # Require JSON?
    # Alerts
    alert_contacts = db.StringListProperty(indexed=False)  # String ID for recipients (sensor specific) to notify
    alert_message = db.TextProperty()
    # Payment (sent upon alert)
    payment_contacts = db.StringListProperty(indexed=False)  # String ID for recipients (sensor specific) to send to
    payment_amount = DecimalProperty(indexed=False)
    # Sleeping (sleep if any of the below)
    sleep_month_days = db.ListProperty(int, indexed=False)  # 1 - 31
    sleep_week_days = db.ListProperty(int, indexed=False)  # 1 - 7 (Mon - Sun)
    sleep_months = db.ListProperty(int, indexed=False)  # 1 - 12
    sleep_hours = db.ListProperty(int, indexed=False) # 00 - 23

    def __repr__(self):
        return "<Rule trigger=%d column=%s>" % (self.trigger, self.column)

    def __str__(self):
        return self.name

    def json(self):
        return {
            'key': str(self.key()),
            'id': self.key().id(),
            'name': self.name,
            'trigger': self.trigger,
            'column': self.column,
            'duration': self.duration,
            'buffer': self.buffer,
            'plimit': self.plimit,
            'plimit_type': self.plimit_type,
            'consecutive': self.consecutive,
            'consecutive_limit': self.consecutive_limit,
            'value1': self.value1,
            'value2': self.value2,
            'value_complex': self.value_complex,
            'alert_message': self.alert_message,
            'alert_contacts': self.alert_contacts,
            'payment_contacts': self.payment_contacts,
            'payment_amount': str(self.payment_amount)
        }

    @staticmethod
    def Fetch(e, sensortype=None, limit=50):
        q = Rule.all().ancestor(e)
        if sensortype:
            q.filter("sensortype =", sensortype)
        return q.fetch(limit=limit)

    @staticmethod
    def Create(e):
        return Rule(parent=e, enterprise=e)

    def Update(self, **params):
        message = None
        if 'name' in params:
            self.name = params['name']
        if 'trigger' in params:
            self.trigger = params['trigger']
        if 'duration' in params:
            self.duration = params['duration']
        if 'consecutive' in params:
            self.consecutive = params['consecutive']
        if 'plimit' in params:
            plimit = params['plimit']
            if plimit > MAX_PLIMIT:
                message = "Period Limit set to maximum of %d" % MAX_PLIMIT
                plimit = MAX_PLIMIT
            self.plimit = params['plimit']
        if 'plimit_type' in params:
            self.plimit_type = params['plimit_type']
        if 'consecutive_limit' in params:
            self.consecutive_limit = params['consecutive_limit']
        if 'buffer' in params:
            self.buffer = params['buffer']
        if 'column' in params:
            self.column = params['column']
        if 'value1' in params:
            self.value1 = float(params['value1'])
        if 'value2' in params:
            self.value2 = float(params['value2'])
        if 'value_complex' in params:
            self.value_complex = json.dumps(params['value_complex'])
        if 'alert_message' in params:
            self.alert_message = params['alert_message']
        if 'alert_contacts' in params:
            self.alert_contacts = params['alert_contacts']
        if 'payment_contacts' in params:
            self.payment_contacts = params['payment_contacts']
        if 'payment_amount' in params:
            self.payment_amount = tools.toDecimal(params['payment_amount'])

        return message

    def payments_enabled(self):
        return self.payment_contacts and self.payment_amount > 0

    def period_limit_enabled(self):
        return self.plimit_type != RULE.DISABLED and self.plimit

    def period_count(self, alarms, record):
        '''Count number of passed alarms in current period (as defined by plimit_type)
        '''
        alarms_in_period = filter(lambda a : tools.in_same_period(tools.unixtime(a.dt_start), record.ts(), period_type=self.plimit_type), alarms)
        return len(alarms_in_period)


    def consecutive_limit_reached(self, n_consecutive):
        limit = self.consecutive_limit
        if limit == RULE.DISABLED:
            return False
        elif limit == RULE.ANY:
            return True
        else:
            return n_consecutive >= limit

    def alarm_condition_passed(self, r, prior_r=None):
        # Check rule status prior to duration/consecutive check
        passed = False
        diff = None
        val = r.columnValue(self.column)
        prior_val = prior_r.columnValue(self.column) if prior_r else None
        if self.trigger == RULE.NO_DATA:
            # This isn't really testing no data
            passed = val is None
        elif self.trigger == RULE.FLOOR:
            floor = self.value1
            passed = val < floor
            if passed:
                diff = floor - val
        elif self.trigger == RULE.CEILING:
            ceiling = self.value2
            passed = val > ceiling
            if passed:
                diff = val - ceiling
        elif self.trigger == RULE.IN_WINDOW:
            window = [self.value1, self.value2]
            passed = val >= window[0] and val <= window[1]
            if passed:
                diff = max([window[0]-val, val-window[1]])
        elif self.trigger == RULE.OUT_WINDOW:
            window = [self.value1, self.value2]
            passed = val < window[0] or val > window[1]
            if passed:
                diff = min([abs(val-window[0]), abs(val-window[1])])
        elif self.trigger == RULE.DELTA_FLOOR:
            dfloor = self.value1
            if prior_val is None:
                passed = False
            else:
                delta = val - prior_val
                passed = delta < dfloor
            if passed:
                diff = dfloor - delta
        elif self.trigger == RULE.DELTA_CEILING:
            dceiling = self.value1
            if prior_val is None:
                passed = False
            else:
                delta = val - prior_val
                passed = delta > dceiling
            if passed:
                diff = delta - dceiling
        elif self.trigger == RULE.ANY_DATA:
            passed = val is not None
        elif self.trigger in [RULE.GEOFENCE_OUT, RULE.GEOFENCE_IN]:
            geo_json = tools.getJson(self.value_complex)
            if geo_json and val:
                polygon = tools.polygon_from_geojson(geo_json)
                gp = tools.safe_geopoint(val)
                if gp:
                    inside = tools.point_inside_polygon(gp.lat, gp.lon, polygon)
                    passed = inside == (self.trigger == RULE.GEOFENCE_IN)
        elif self.trigger in [RULE.GEORADIUS_OUT, RULE.GEORADIUS_IN]:
            geo_value = tools.getJson(self.value_complex)
            if geo_value and val:
                gp = tools.safe_geopoint(val)
                if gp and 'lat' in geo_value and 'lon' in geo_value:
                    inside = tools.point_within_radius(gp.lat, gp.lon, float(geo_value.get('lat')), float(geo_value.get('lon')), radius_m=self.value2)
                    passed = inside == (self.trigger == RULE.GEORADIUS_IN)
        else:
            raise Exception("Unsupported trigger type: %s" % self.trigger)
        # logging.debug("%s %s at value: %s (diff %s)" % (self, "passed" if passed else "not passed", val, diff))
        return (passed, diff, val)

    def get_message(self):
        if self.alert_message:
            return self.alert_message
        else:
            # Standard message
            return "Alert - {rule.name} for {sensor.name} at {start.time}"

    def clean_delete(self):
        db.delete(self.alarm_set.fetch(limit=None))
        self.delete()


class Analysis(db.Expando):
    """
    Parent - Enterprise
    Key - name - [name specified by ProcessTask() spec]
    Record of summary (can be calculated during process)
    """
    enterprise = db.ReferenceProperty(Enterprise)
    sensor = db.ReferenceProperty(Sensor)
    sensortype = db.ReferenceProperty(SensorType)
    label = db.StringProperty(indexed=False)
    dt_created = db.DateTimeProperty(auto_now_add=True)
    dt_updated = db.DateTimeProperty(auto_now_add=True)


    def __repr__(self):
        return "<Analysis kn=%s>" % self.key().name()

    def json(self, with_props=True):
        res = {
            'key': str(self.key()),
            'kn': self.key().name(),
            'ts_created': tools.unixtime(self.dt_created),
            'ts_updated': tools.unixtime(self.dt_updated) if self.dt_updated else None,
            'sensor_kn': tools.getKey(Analysis, 'sensor', self, asID=False, asKeyName=True)
        }
        if with_props:
            res['columns'] = {}
            for prop in self.dynamic_properties():
                res['columns'][prop] = self.columnValue(prop)
        return res


    def columnValue(self, column, default=None):
        return getattr(self, column, default)

    def setColumnValue(self, column, value):
        # logging.debug("%s: Setting %s to %s (%s)" % (self, column, value, type(value)))
        self.dt_updated = datetime.now()
        setattr(self, column, value)

    @staticmethod
    def _key_name(analysis_key_pattern, sensor=None):
        now = datetime.now()
        REPL = [
            ('%SID', sensor.key().name() if sensor else ""),
            ('%Y', datetime.strftime(now, '%Y')),
            ('%M', datetime.strftime(now, '%m')),
            ('%D', datetime.strftime(now, '%d')),
            ('%W', datetime.strftime(now, '%W')) # Python style week number (0-53)
        ]
        for rep in REPL:
            analysis_key_pattern = analysis_key_pattern.replace(rep[0], rep[1])
        return analysis_key_pattern

    @staticmethod
    def Get(e, kn):
        return Analysis.get_by_key_name(kn, parent=e)

    @staticmethod
    def GetOrCreate(sensor, analysis_key_pattern):
        '''
        Pass one of analysis_key_pattern or kn
        '''
        kn = Analysis._key_name(analysis_key_pattern, sensor=sensor)
        a = Analysis.get_or_insert(kn, parent=sensor.enterprise, enterprise=sensor.enterprise, sensor=sensor, sensortype=sensor.sensortype)
        return a

    @staticmethod
    def Fetch(enterprise=None, sensor=None, sensortype_id=None, limit=50):
        if sensor:
            return sensor.analysis_set.order("-dt_created").fetch(limit=limit)
        elif enterprise:
            q = enterprise.analysis_set.order("-dt_created")
            if sensortype_id:
                q.filter("sensortype =", db.Key.from_path('SensorType', sensortype_id, parent=enterprise.key()))
            return q.fetch(limit=limit)
        else:
            return []

    def Update(self, **params):
        pass

class ProcessTask(UserAccessible):
    """
    Parent - Enterprise
    Key - ID

    Definition of intermittent processing task
    Can be defined to produce Analysis() as output
    Alarm()s defined by rule_ids are checked during processing

    spec is object with properties processers (array<processer>)
    where <processer> is an object with properties:
     * calculation/expr - an ExpressionParser() parsable expression. Examples:
        - "AVE({speed})": Average of all speed values in processed set
        - "MAX({temp})": Maximum temperature of all values in processed set
        - ". + SUM({values})": Increment current value with sum of all new values
     * analysis_key_pattern - suffix for Analysis() key name. Can include variables:
        - %SID: sensor ID
        - %Y: year (e.g. '2015')
        - %M: month (e.g. '04')
        - %D: day (e.g. '09')
     * column - column name for Analysis()
    """
    enterprise = db.ReferenceProperty(Enterprise)
    dt_created = db.DateTimeProperty(auto_now_add=True)
    # Run every 'interval' seconds between 'time_start' and 'time_end'
    interval = db.IntegerProperty(default=120)  # Seconds
    time_start = db.TimeProperty(indexed=False)  # UTC
    time_end = db.TimeProperty(indexed=False)  # UTC
    # Scheduling - OR of the below
    month_days = db.ListProperty(int, indexed=False)  # 1 - 31
    week_days = db.ListProperty(int, default=[1,2,3,4,5,6,7], indexed=False)  # 1 - 7 (Mon - Sun)
    rule_ids = db.ListProperty(int, indexed=False)
    label = db.StringProperty(indexed=False)
    # JSON spec for ExpressionParser (cleaning, calculations, and production of analysis records). TODO: Validate
    spec = db.TextProperty()

    def __repr__(self):
        return "<ProcessTask label=%s>" % self.label

    def __str__(self):
        return self.label if self.label else "Processer (%ss)" % self.interval

    def json(self):
        return {
            'key': str(self.key()),
            'id': self.key().id(),
            'label': self.label,
            'interval': self.interval,
            'rule_ids': self.rule_ids,
            'month_days': self.month_days,
            'week_days': self.week_days,
            'time_start': tools.stime(self.time_start),
            'time_end': tools.stime(self.time_end),
            'spec': self.spec
        }

    def get_processers(self):
        spec = tools.getJson(self.spec)
        if spec and 'processers' in spec:
            return spec['processers']
        return []

    def get_sensor_tasks(self, limit=None):
        return self.sensorprocesstask_set.fetch(limit=limit)

    def get_rules(self):
        return [rule for rule in Rule.get_by_id(self.rule_ids, parent=self.enterprise) if rule]

    def can_run_now(self):
        today_ok = self.runs_today()
        if today_ok:
            now = datetime.now()
            now_ok = (not self.time_start or now.time() >= self.time_start) and \
                (not self.time_end or now.time() < self.time_end)
            return now_ok
        return False

    def runs_today(self, day_offset=0):
        now = datetime.now()
        if day_offset:
            now = now + timedelta(days=day_offset)
        day_of_week = now.weekday() + 1 # 1-7 M-Su
        day_of_month = now.day
        return day_of_week in self.week_days or day_of_month in self.month_days

    def duplicate(self):
        new_pt = tools.clone_entity(self,
           parent=self.parent(),
           label="Copy of " + self.label
        )
        return new_pt

    @staticmethod
    def Create(e):
        return ProcessTask(parent=e, enterprise=e)

    @staticmethod
    def Fetch(e, limit=50):
        return e.processtask_set.fetch(limit=limit)

    def Update(self, **params):
        if 'spec' in params:
            self.spec = json.dumps(params['spec'])
        if 'interval' in params:
            MIN_INTERVAL = 60
            interval = params['interval']
            if interval < MIN_INTERVAL:
                interval = MIN_INTERVAL
            self.interval = interval
        if 'month_days' in params:
            self.month_days = [int(md) for md in params['month_days']]
        if 'week_days' in params:
            self.week_days = [int(wd) for wd in params['week_days']]
        if 'time_start' in params:
            self.time_start = params['time_start']
        if 'time_end' in params:
            self.time_end = params['time_end']
        if 'label' in params:
            self.label = params['label']
        if 'rule_ids' in params:
            self.rule_ids = [int(aid) for aid in params['rule_ids']]


class SensorProcessTask(db.Model):
    """
    Parent - Enterprise
    Key Name - [process ID]_[sensor kn]
    Join of ProcessTask() and Sensor() to identify processing tasks to perform
    and maintain state for each sensor & process
    """
    enterprise = db.ReferenceProperty(Enterprise)
    process = db.ReferenceProperty(ProcessTask)
    sensor = db.ReferenceProperty(Sensor)
    dt_created = db.DateTimeProperty(auto_now_add=True)
    dt_last_run = db.DateTimeProperty(default=None)
    dt_last_record = db.DateTimeProperty(default=None)
    status_last_run = db.IntegerProperty(default=PROCESS.NEVER_RUN)
    narrative_last_run = db.TextProperty()

    def __repr__(self):
        return "<SensorProcess sensor=%s process=%s />" % (self.sensor, self.process)

    def __str__(self):
        return "Processer for %s" % self.sensor

    def json(self):
        return {
            'key': str(self.key()),
            'label': str(self),
            'ts_last_run': tools.unixtime(self.dt_last_run),
            'ts_last_record': tools.unixtime(self.dt_last_record),
            'status_last_run': self.status_last_run,
            'narrative_last_run': self.narrative_last_run
        }

    def print_status(self):
        return PROCESS.STATUS_LABELS.get(self.status_last_run)

    @staticmethod
    def _key_name(process, sensor):
        return "%s_%s" % (process.key().id(), sensor.key().name())

    @staticmethod
    def Create(e, process, sensor):
        kn = SensorProcessTask._key_name(process, sensor)
        sp = None
        if kn:
            sp = SensorProcessTask(key_name=kn, parent=e, enterprise=e, sensor=sensor, process=process)
        return sp

    @staticmethod
    def Get(process, sensor):
        kn = SensorProcessTask._key_name(process, sensor)
        return SensorProcessTask.get_by_key_name(kn, parent=sensor.enterprise)

    @staticmethod
    @auto_cache()
    def Fetch(sensor=None, enterprise=None, limit=50):
        if sensor:
            return sensor.sensorprocesstask_set.fetch(limit=limit)
        elif enterprise:
            return SensorProcessTask.all().ancestor(enterprise).order("-dt_last_run").fetch(limit=limit)
        else:
            return []

    def should_run(self):
        if self.dt_last_run:
            if self.sensor.dt_updated:
                return self.dt_last_run < self.sensor.dt_updated
            else:
                return False
        else:
            return True

    def schedule_run(self):
        from tasks import bgRunSensorProcess
        process = self.process
        if process.can_run_now():
            mins = max([int(process.interval / 60.), 1])
            tools.add_batched_task(bgRunSensorProcess, str(self.key()), interval_mins=mins, sptkey=str(self.key()))
        else:
            logging.info("%s can't run now" % self)

    def run(self):
        # Start the worker in the background
        if self.should_run():
            logging.info("Running %s" % self)
            from tasks import bgRunSensorProcess
            tools.safe_add_task(bgRunSensorProcess, sptkey=str(self.key()))
            return True
        else:
            logging.debug("No need to run %s" % self)
            return False

    def clean_delete(self):
        self.delete()
        return True

class Payment(UserAccessible):
    """
    Payment to or from a user (e.g. for incentives)

    Parent - Enterprise
    Key - ID
    """
    dt_created = db.DateTimeProperty(auto_now_add=True)
    dt_updated = db.DateTimeProperty()
    enterprise = db.ReferenceProperty(Enterprise)
    user = db.ReferenceProperty(User)
    amount = DecimalProperty()
    currency = db.StringProperty(default="USD")
    direction = db.IntegerProperty(default=PAYMENT.TO)
    status = db.IntegerProperty(default=PAYMENT.REQUESTED)
    gateway_id = db.StringProperty()
    last_gateway_response = db.TextProperty()
    channel = db.IntegerProperty(default=PAYMENT.AIRTIME)

    def __str__(self):
        return "%s %s payment %s %s (%s)" % (self.currency, self.amount, self.print_direction(), self.user, self.print_channel())

    def json(self, with_user=False):
        res = {
            'id': self.key().id(),
            'ts_created': tools.unixtime(self.dt_created),
            'amount': str(self.amount),
            'currency': self.currency,
            'status': self.status,
            'channel': self.channel
        }
        if with_user and self.user:
            res['user'] = self.user.json()
        return res

    @staticmethod
    def Request(ent, user, amount, channel=PAYMENT.AIRTIME):
        currency = user.currency
        pmnt = None
        if currency:
            if ent and user and amount:
                pmnt = Payment(parent=ent, enterprise=ent, user=user, amount=amount, currency=currency, channel=channel)
                pmnt.put()
                pmnt.send()
        else:
            logging.error("No currency for user")
        return pmnt

    @staticmethod
    def Fetch(ent=None, user=None, limit=50):
        if ent:
            return ent.payment_set.order("-dt_created").fetch(limit=limit)
        elif user:
            return user.payment_set.order("-dt_created").fetch(limit=limit)
        else:
            return []

    def send(self):
        success = False
        if self.can_send():
            if self.channel == PAYMENT.AIRTIME:
                if self.user.phone:
                    success, self.last_gateway_response, self.gateway_id = outbox.send_airtime(self.enterprise, self.user.phone, self.amount, self.currency)
                    if success:
                        self.confirm_sent()
                        self.put() # Note, duplicate put
                else:
                    logging.error("Can't send to user, no phone")
        return success

    def confirm_sent(self):
        self.status = PAYMENT.SENT

    def can_send(self):
        return self.status == PAYMENT.REQUESTED

    def print_direction(self):
        return PAYMENT.DIRECTION_LABELS.get(self.direction)

    def print_channel(self):
        return PAYMENT.CHANNEL_LABELS.get(self.channel)

    def print_status(self):
        return PAYMENT.STATUS_LABELS.get(self.status)

class Record(db.Expando):
    """
    Parent - Sensor
    Key - Name: timestamp (ms, avoid duplicates)
    With abstract dynamic columns defined by sensor's schema
    """
    enterprise = db.ReferenceProperty(Enterprise)
    sensor = db.ReferenceProperty(Sensor)
    sensortype = db.ReferenceProperty(SensorType)
    target = db.ReferenceProperty(Target)
    dt_recorded = db.DateTimeProperty()  # Real time in UTC (from timestamp)
    dt_created = db.DateTimeProperty(auto_now_add=True)  # Hit server
    minute = db.IntegerProperty()  # Minutes since UTC epoch (for downsample)
    hour = db.IntegerProperty()  # Minutes since UTC epoch (for downsample)

    def __repr__(self):
        return "<Record kn=%s />" % self.key().name()

    def json(self, with_props=True, props_only=False):
        res = {}
        if not props_only:
            res = {
                'kn': self.key().name(),
                'ts': tools.unixtime(self.dt_recorded),
                'ts_created': tools.unixtime(self.dt_created),
                'sensor_key': tools.getKey(Record, 'sensor', self, asID=False)
            }
        if with_props:
            res['columns'] = {}
            for prop in self.columns():
                res['columns'][prop] = self.columnValue(prop)
        return res

    def columns(self):
        return self.dynamic_properties()

    def columnValue(self, column, default=None):
        return getattr(self, column, default)

    def setColumnValue(self, column, value, _type=None):
        if _type:
            if _type == 'number':
                value = tools.safe_number(value)
        setattr(self, column, value)

    def ts(self):
        return tools.unixtime(self.dt_recorded)
    @staticmethod

    def Get(enterprise, sensor_kn, kn):
        key = db.Key.from_path('Enterprise', enterprise.key().id(), 'Sensor', sensor_kn, 'Record', kn)
        if key:
            return Record.get(key)
        return None

    @staticmethod
    def Fetch(sensor, limit=50, dt_start=None, dt_end=None, downsample=DOWNSAMPLE.NONE):
        '''Takes sensor as Sensor() or Key

        Note that unindexed downsamples (see DOWNSAMPLE()) uses limit for the initial fetch,
        but will return less records after post-query filtering.

        Args:
            dt_start (datetime): Start of date filter range
            dt_end (datetime): End of date filter range
            downsample (int): Optional downsample

        Returns:
            List of Record() objects (most recent first)
        '''
        if downsample:
            ds_prop = DOWNSAMPLE.PROPERTIES.get(downsample)
            projection = [ds_prop]
            distinct = True
        else:
            ds_prop = None
            projection = None
            distinct = False
        q = db.Query(Record, projection=projection, distinct=distinct).ancestor(sensor)

        if downsample:
            q.order("-"+ds_prop)
            ms_per = DOWNSAMPLE.MS_PER.get(downsample)
            if dt_start:
                start = tools.unixtime(dt_start) / ms_per
                q.filter(ds_prop+" >=", start)
            if dt_end:
                end = tools.unixtime(dt_end) / ms_per
                q.filter(ds_prop+" <=", end)

            prop_divider = 0
            if downsample in DOWNSAMPLE.UNINDEXED:
                # Manual downsampling using dict keys
                prop_divider = DOWNSAMPLE.UNINDEXED_PROP_DIVIDER.get(downsample)
            # Multiply limit if we're doing an unindexed downsample since we will lose
            # records in the filtering.
            if prop_divider:
                limit *= prop_divider
            # Query returns keys of downsampled records
            proj_records = q.fetch(limit=limit)
            if prop_divider:
                unique_by_period = {}
                for rec in proj_records:
                    ds_value = getattr(rec, ds_prop, 0)
                    if type(ds_value) in [float, int, long]:
                        rec.ds_period = ds_value / prop_divider
                        unique_by_period[rec.ds_period] = rec
                proj_records = sorted(unique_by_period.values(), key=lambda r : r.ds_period, reverse=True)
            return Record.get([x.key() for x in proj_records])
        else:
            q.order("-dt_recorded")
            if dt_start:
                q.filter("dt_recorded >=", dt_start)
            if dt_end:
                q.filter("dt_recorded <=", dt_end)
            # Query returns Record() list
            return q.fetch(limit=limit)

    @staticmethod
    def Create(ts, sensor, data, apply_roles=False, schema=None, expression_parser_by_col={}, put=False, allow_future=False):
        r = None
        if not schema:
            schema = sensor.sensortype.get_schema()
        kn = str(int(ts)) # ms
        ms_ago = tools.unixtime() - ts
        sane_ts = allow_future or ms_ago > -60*1000 # Sanity: timestamp in past with 60 second buffer
        if not sane_ts:
            logging.warning("Non-sane ts in Record.Create, not creating: %s" % ts)
        else:
            if kn and schema:
                minute = int(ts / 1000 / 60)
                hour = int(minute / 60)
                targetkey = tools.getKey(Sensor, 'target', sensor, asID=False, keyObj=True)
                sensortypekey = tools.getKey(Sensor, 'sensortype', sensor, asID=False, keyObj=True)
                r = Record(key_name=kn, parent=sensor, sensor=sensor, target=targetkey, sensortype=sensortypekey, dt_recorded=tools.dt_from_ts(ts), minute=minute, hour=hour, enterprise=sensor.enterprise)
                # First pass extracts record data as defined by schema, and creates dict of pending calculations
                calculations = {}
                for column, colschema in schema.items():
                    if 'calculation' in colschema:
                        calc = colschema.get('calculation')
                        if calc:
                            calculations[column] = calc
                            continue  # We'll perform calculations in next pass
                    if column in data:
                        val = data[column]
                        r.setColumnValue(column, val, colschema.get('type'))
                        if apply_roles:
                            roles = colschema.get('role', [])
                            if roles:
                                for role in roles:
                                    sensor.update_state(role, val)
                                    if sensor.target:
                                        sensor.target.update_state(role, val)
                if calculations:
                    for column, calc in calculations.items():
                        # Faster to build each parser once and pass in
                        ep = expression_parser_by_col.get(column)
                        if not ep:
                            ep = ExpressionParser(calc, column)
                        res = ep.run(record=r)
                        r.setColumnValue(column, res)
                if put:
                    r.put()
            else:
                logging.warning("Missing kn or schema")
        return r

class Alarm(db.Model):
    """
    Parent - Sensor
    Key - ID
    Single alarm event for a sensor
    """
    enterprise = db.ReferenceProperty(Enterprise)
    sensor = db.ReferenceProperty(Sensor)
    target = db.ReferenceProperty(Target)
    rule = db.ReferenceProperty(Rule)
    first_record = db.ReferenceProperty(Record)
    apex = db.FloatProperty()  # Most extreme value during alarm period
    dt_start = db.DateTimeProperty() # Activation
    dt_end = db.DateTimeProperty() # Deactivation

    def __repr__(self):
        return "<Alarm dt_start=%s rule=%s >" % (tools.sdatetime(self.dt_start), self.rule)

    def __str__(self):
        return self.rule.name

    def json(self, with_props=None):
        if not with_props:
            with_props = []
        res = {
            'key': str(self.key()),
            'id': self.key().id(),
            'ts_start': tools.unixtime(self.dt_start),
            'ts_end': tools.unixtime(self.dt_end),
            'rule_name': self.rule.name,
            'rule_id': tools.getKey(Alarm, 'rule', self, asID=True),
            'rule_column': self.rule.column,
            'sensor_key': tools.getKey(Alarm, 'sensor', self, asID=False),
            'sensor_kn': tools.getKey(Alarm, 'sensor', self, asID=False, asKeyName=True),
            'first_record_kn': tools.getKey(Alarm, 'first_record', self, asID=False, asKeyName=True),
            'apex': self.apex
        }
        if 'sensor_name' in with_props:
            res['sensor_name'] = self.sensor.name
        return res


    @staticmethod
    def Create(sensor, rule, record, notify=True):
        start = record.dt_recorded
        a = Alarm(parent=sensor, sensor=sensor, target=sensor.target, rule=rule, enterprise=sensor.enterprise, dt_start=start, dt_end=start, first_record=record)
        value = record.columnValue(rule.column)
        a.set_apex(value)
        if notify:
            a.notify_contacts()
        if rule.payments_enabled():
            a.request_payments()
        logging.debug("### Creating alarm '%s'! ###" % a)
        return a

    @staticmethod
    def Delete(sensor=None, rule_id=None, limit=300):
        to_delete = []
        if sensor:
            q = Alarm.all(keys_only=True).filter("sensor =", sensor)
            if rule_id:
                q.filter("rule =", db.Key.from_path('Rule', rule_id, parent=tools.getKey(Sensor, 'enterprise', sensor, asID=False, keyObj=True)))
            to_delete = q.fetch(limit=limit)
        if to_delete:
            db.delete(to_delete)
        return len(to_delete)

    @staticmethod
    def Fetch(sensor=None, enterprise=None, rule=None, limit=50):
        if sensor:
            q = sensor.alarm_set.order("-dt_start")
        elif enterprise:
            q = enterprise.alarm_set.order("-dt_start")
        else:
            return []
        if rule:
            q.filter("rule =", rule)
        return q.fetch(limit=limit)

    # TODO: is this used?
    def deactivate(self, end):
        self.dt_end = end

    def set_apex(self, value):
        '''
        Value is a pure Record() property
        '''
        try:
            self.apex = float(value)
        except:
            logging.debug("Failed to set apex to %s" % value)

    def duration(self):
        '''
        Returns timedelta or None
        '''
        if self.dt_end and self.dt_start:
            return self.dt_end - self.dt_start
        return None

    def render_alert_message(self, recipient=None):
        '''
        Converts message with variables to sendable format, e.g.:
        'Hello {to.name}, device {sensor.name} was above normal limits at {start.datetime}'
        ->
        'Hello John, device 00-100 was above normal limits at 2015-08-02 12:34'
        recipient is either a dict of contact info, or a User() object
        '''
        message = self.rule.get_message()
        sensor = self.sensor
        rule = self.rule
        tz = self.enterprise.get_timezone()
        recipient_name = ""
        if type(recipient) is User:
            if recipient.name:
                recipient_name = recipient.name
        elif type(recipient) is dict:
            recipient_name = recipient.get('name', '') if recipient else ''
        replacements = {
            'to.name': recipient_name,
            'rule.name': rule.name,
            'sensor.name': sensor.name,
            'sensor.id': sensor.key().name(),
            'start.date': tools.sdatetime(self.dt_start, fmt="%Y-%m-%d", tz=tz),
            'start.datetime': tools.sdatetime(self.dt_start, fmt="%Y-%m-%d %H:%M", tz=tz),
            'start.time': tools.sdatetime(self.dt_start, fmt="%H:%M", tz=tz),
            'record.first.alarm_value': self.first_record_value
        }
        return tools.variable_replacement(message, replacements)

    def first_record_value(self):
        if self.first_record:
            return self.first_record.columnValue(self.rule.column)
        return None

    def notify_contacts(self):
        if self.rule.alert_contacts and self.rule.get_message():
            recipients = User.UsersFromSensorContactIDs(self.sensor, self.rule.alert_contacts)
            for recipient in recipients:
                rendered_message = self.render_alert_message(recipient=recipient)
                outbox.send_message(recipient, rendered_message, additional_params={
                    'rule_id': self.rule.key().id()
                })
        return self.rule.alert_contacts

    def request_payments(self):
        recipients = User.UsersFromSensorContactIDs(self.sensor, self.rule.payment_contacts)
        for recipient in recipients:
            Payment.Request(self.rule.enterprise, recipient, self.rule.payment_amount)
        return self.rule.payment_contacts


class Report(UserAccessible):
    """
    Parent - Enterprise
    Key - ID
    """
    enterprise = db.ReferenceProperty(Enterprise)
    dt_created = db.DateTimeProperty(auto_now_add=True)
    dt_generated = db.DateTimeProperty()
    blob_key = db.StringProperty(indexed=False) # Report data
    gcs_files = db.StringListProperty(indexed=False, default=[])
    title = db.StringProperty()
    storage_type = db.IntegerProperty(default=REPORT.GCS_CLIENT, indexed=False)
    status = db.IntegerProperty(default=REPORT.CREATED)
    type = db.IntegerProperty(default=REPORT.SENSOR_DATA_REPORT)
    ftype = db.IntegerProperty(default=REPORT.XLS, indexed=False)
    extension = db.StringProperty(default="xls", indexed=False)
    specs = db.TextProperty() # JSON, e.g. date filters etc

    def __str__(self):
        return "%s (%s)" % (self.title, self.printType())

    def json(self):
        return {
            'key': str(self.key()),
            'id': self.key().id(),
            'title': self.title,
            'status': self.status,
            'serve_url': self.serving_url(),
            'type': self.type,
            'ftype': self.ftype,
            'extension': self.extension,
            'ts_created': tools.unixtime(self.dt_created),
            'ts_generated': tools.unixtime(self.dt_generated),
            'filenames': self.gcs_files
        }

    @staticmethod
    def Fetch(e, limit=50):
        return Report.all().ancestor(e).order("-dt_created").fetch(limit=limit)

    def getDuration(self):
        if self.dt_created and self.dt_generated:
            return tools.total_seconds(self.dt_generated - self.dt_created)
        return 0

    def getSpecs(self):
        if self.specs:
            return json.loads(self.specs)
        return {}

    def isDone(self):
        return self.status == REPORT.DONE

    def isGenerating(self):
        return self.status == REPORT.GENERATING

    def setSpecs(self, data):
        self.specs = json.dumps(data)

    def generate_title(self, _title, ts_start=None, ts_end=None, **kwargs):
        title = _title
        start_text = end_text = None
        if ts_start:
            start_text = tools.sdatetime(tools.dt_from_ts(ts_start))
        if ts_end:
            end_text = tools.sdatetime(tools.dt_from_ts(ts_end))
        if start_text and end_text:
            title += " (%s - %s)" % (start_text, end_text)
        elif start_text:
            title += " Since %s" % start_text
        elif end_text:
            title += " Until %s" % end_text
        for key, val in kwargs.items():
            if key and val is not None:
                title += " %s:%s" % (key, val)
        self.title = title

    def filename(self, ext=None, piece=None):
        _piece = ""
        if piece is not None:
            _piece = self.gcs_filenames[piece-1]
        _ext = ext if ext else self.extension
        fn = "%s%s.%s" % (self.title, _piece, _ext)
        return fn

    def getExtension(self):
        self.extension = REPORT.EXTENSIONS.get(self.ftype)

    @staticmethod
    def Create(ent, title="Unnamed Report", type=REPORT.SENSOR_DATA_REPORT, specs=None, ftype=None):
        logging.debug("Requesting report creation, type %d specs: %s" % (type, specs))
        r = Report(title=title, type=type, enterprise=ent, parent=ent)
        if specs:
            r.setSpecs(specs)
        r.storage_type = REPORT.GCS_CLIENT
        if ftype is not None:
            r.ftype = ftype
        else:
            r.ftype = REPORT.CSV
        r.getExtension()
        return r

    def printType(self): return REPORT.TYPE_LABELS.get(self.type)

    def printStatus(self): return REPORT.STATUS_LABELS.get(self.status)

    @staticmethod
    def contentType(extension):
        if extension in ['xls', 'xlsx']:
            return "application/ms-excel"
        elif extension == 'csv':
            return "text/csv"
        elif extension == 'pdf':
            return "application/pdf"
        else:
            return None

    def run(self, target, start_cursor=None, acc=None):
        """Begins report generation"""
        if self.type == REPORT.SENSOR_DATA_REPORT:
            from reports import SensorDataReportWorker
            worker = SensorDataReportWorker(target, self.key())
        elif self.type == REPORT.ALARM_REPORT:
            from reports import AlarmReportWorker
            worker = AlarmReportWorker(target, self.key())
        elif self.type == REPORT.ANALYSIS_REPORT:
            from reports import AnalysisReportWorker
            worker = AnalysisReportWorker(target, self.key())
        elif self.type == REPORT.APILOG_REPORT:
            from reports import APILogReportWorker
            worker = APILogReportWorker(self.key())
        else:
            worker = None
        if worker and self.status not in [REPORT.ERROR, REPORT.CANCELLED]:
            worker.run(start_cursor=start_cursor)
        else:
            logging.error("Worker not created or invalid status for run(): type %d" % self.type)

    def finish(self):
        '''Finalize report'''
        self.status = REPORT.DONE
        self.dt_generated = datetime.now()

    def serving_url(self):
        url = None
        if self.storage_type == REPORT.GCS_CLIENT:
            # url = webapp2.uri_for('ServeGCSReport', rkey=self.key())
            # Strange bug: "Route named 'ServeGCSReport' is not defined."
            url = "/api/report/serve?rkey=%s" % self.key()
        return url

    def getGCSFile(self, index=0):
        # we actually don't anticipate more than 1 gcsfiles anymore
        if self.gcs_files and len(self.gcs_files) >= index + 1:
            return self.gcs_files[index]
        return None

    def deleteBlob(self):
        if self.blob_key:
            resource = str(urllib.unquote(self.blob_key))
            blob_info = blobstore.BlobInfo.get(resource)
            if blob_info:
                blob_info.delete()
            self.blob_key = None

    def deleteGCSFiles(self):
        import cloudstorage as gcs
        if self.gcs_files:
            for f in self.gcs_files:
                try:
                    gcs.delete(f)
                    self.gcs_files.remove(f)
                except gcs.NotFoundError, e:
                    logging.debug("File %s not found on gcs" % f)

    def CleanDelete(self, self_delete=True):
        self.deleteBlob()
        self.deleteGCSFiles()
        if self_delete:
            db.delete(self)

class APILog(UserAccessible):
    """
    Parent - Enterprise
    Key - ID
    """
    enterprise = db.ReferenceProperty(Enterprise)
    user = db.ReferenceProperty(User)
    # Request
    host = db.TextProperty()
    path = db.TextProperty()
    status = db.IntegerProperty(indexed=False)
    request = db.TextProperty() # With authentication params stripped
    method = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    # Response
    success = db.BooleanProperty(indexed=False)
    message = db.TextProperty()

    def json(self):
        return {
            'id': self.key().id(),
            'ts': tools.unixtime(self.date),
            'host': self.host,
            'path': self.path,
            'method': self.method,
            'status': self.status,
            'request': self.request,
            'success': self.success,
            'message': self.message
        }

    @staticmethod
    def Create(request, user=None, enterprise=None, status=200, success=None, message=None):
        try:
            path = request.path
            host = request.host
            method = request.method
            AUTH_PARAMS = ['auth', 'password', 'uid', 'pw']  # To not be included in log
            req = {}
            for arg in request.arguments():
                if arg not in AUTH_PARAMS:
                    try:
                        req[arg] = request.get(arg)
                    except Exception, ex:
                        logging.warning("Unable to log arg: %s (%s)" % (arg, ex))
            if path and (user or enterprise):
                if not enterprise:
                    enterprise = user.enterprise
                al = APILog(path=path, user=user, enterprise=enterprise, parent=enterprise, status=status, method=method, host=host, request=json.dumps(req), message=message)
                if success is not None:
                    al.success = success
                if al:
                    al.put()
                return al
            return None
        except Exception, e:
            logging.error("Error creating APILog: %s" % e)
            return None

    @staticmethod
    def Recent(enterprise, _max=20):
        q = APILog.all().filter("enterprise =", enterprise).order("-date")
        return q.fetch(_max)