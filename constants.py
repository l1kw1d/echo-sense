
# General info

COMPANY_NAME = "Echo Mobile"
SITENAME = "Echo Sense"
EMAIL_PREFIX = "[ %s ] " % SITENAME
APPNAME = "echo-sense"
BASE = "http://%s.appspot.com" % APPNAME
API_AUTH = "bluep4tches"
PLAY_STORE_LINK = ""

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Branding

CL_PRIMARY = "#409777"
CL_PRIMARY_DK = "#275D4A"

# Emails
APP_OWNER = "onejgordon@gmail.com" # This should be an owner of the cloud project
INSTALL_PW = "REPLACEWITHYOURPASSWORD"
ADMIN_EMAIL = APP_OWNER
ERROR_EMAIL = APP_OWNER
NOTIF_EMAILS = [APP_OWNER]
SENDER_EMAIL = "%s Notifications <noreply@%s.appspotmail.com>" % (SITENAME, APPNAME)

WARN_BATT_LEVEL = 0.15

GA_ID = "UA-34753309-3"

DEFAULT_RATES = ["KES","RWF"]

ALERT_VIA_USERS = True
DEBUG_API = False

# Memkeys
MC_FOREX = "FOREX"

FTS_INDEX = "FTS_EID:%s"

# Google OAuth
ANDROID_CLIENT_ID = ""
ANDROID_CLIENT_ID_DEBUG = ""
KEY_FOR_SERVER_APPLICATIONS = ""

MC_GOOGLE_KEY_CERT_DICT = "GOOGLE_KEY_CERT_DICT"
GP_CLIENT_ID = ""
GP_CLIENT_SECRET = ""
TOKEN_AUD = GP_CLIENT_ID # Web Component
TOKEN_AZP = [ANDROID_CLIENT_ID, ANDROID_CLIENT_ID_DEBUG]

TEST_VERSIONS = ["test"]

BILLING_DAYS_PER_MO = 30

MAX_REQUEST_SECONDS = 40
MAX_PLIMIT = 20

PROJECT_ID = 195674861419 # Also GCM Sender ID

GCS_MEDIA_BUCKET = "/echosense_media"
GCS_REPORT_BUCKET = "/echosense_reports"

# Periods
MS_PER_SECOND = 1000
MS_PER_MINUTE = MS_PER_SECOND * 60
MS_PER_HOUR = MS_PER_MINUTE * 60
MS_PER_DAY = MS_PER_HOUR * 24

class DOWNSAMPLE():
    NONE = 0
    MINUTE = 1
    FIVE_MINUTE = 2
    TEN_MINUTE = 3
    HOUR = 4

    # Indexed
    PROPERTIES = {
        MINUTE: "minute",
        HOUR: "hour",
        FIVE_MINUTE: "minute",
        TEN_MINUTE: "minute"
    }

    MS_PER = {
        MINUTE: MS_PER_MINUTE,
        HOUR: MS_PER_HOUR,
        FIVE_MINUTE: MS_PER_MINUTE,
        TEN_MINUTE: MS_PER_MINUTE
    }

    INDEXED = [MINUTE, HOUR]
    UNINDEXED = [FIVE_MINUTE, TEN_MINUTE]

    UNINDEXED_PROP_DIVIDER = {
        TEN_MINUTE: 10,
        FIVE_MINUTE: 5
    }

class REPORT():
    # Types
    SENSOR_DATA_REPORT = 1
    ALARM_REPORT = 2
    ANALYSIS_REPORT = 3
    APILOG_REPORT = 4

    #status
    CREATED = 1
    GENERATING = 2
    DONE = 3
    CANCELLED = 4
    ERROR = 5

    # STORAGE TYPES
    BLOBSTORE = 1
    GCS_CLIENT = 2

    # Ftypes
    CSV = 1
    XLS = 2
    XLSX = 3
    PDF = 4

    XLS_ROW_LIMIT = 65000

    TYPE_LABELS = {
        SENSOR_DATA_REPORT: "Device Data",
        ALARM_REPORT: "Alarm Report",
        ANALYSIS_REPORT: "Analysis Report",
        APILOG_REPORT: "API Log Report"
    }
    STATUS_LABELS = {CREATED:"Created", GENERATING: "Generating", DONE:"Done", CANCELLED: "Cancelled", ERROR: "Error"}
    EXTENSIONS = {CSV: "csv", XLS: "xls", XLSX: "xlsx", PDF: "pdf"}

class MEDIA():
  PHOTO = 1
  VIDEO = 2

  # Status
  LOCAL = 1
  SAVED = 2

  # Storage
  GCS = 1

class COLUMN():
    # Roles
    LOCATION = 1
    COLOR = 2
    SIZE = 3
    BEARING = 4
    GAUGE = 5


class PROCESS():
    # Statuses for SensorProcess()
    NEVER_RUN = 1
    OK = 2
    WARNING = 3
    ERROR = 4

    STATUS_LABELS = { NEVER_RUN: "Never Run", OK: "OK", WARNING: "Warning", ERROR: "Error" }

class RULE():
  # Trigger
  NO_DATA = 1
  FLOOR = 2
  CEILING = 3
  IN_WINDOW = 4
  OUT_WINDOW = 5
  DELTA_FLOOR = 6
  DELTA_CEILING = 7
  ANY_DATA = 8
  GEOFENCE_OUT = 9
  GEOFENCE_IN = 10
  GEORADIUS_OUT = 11
  GEORADIUS_IN = 12

  TRIGGER_LABELS = {
    NO_DATA: "No Data (To Implement)",
    FLOOR: "Floor",
    CEILING: "Ceiling",
    IN_WINDOW: "In Window",
    OUT_WINDOW: "Out Window",
    DELTA_FLOOR: "Delta Floor",
    DELTA_CEILING: "Delta Ceiling",
    ANY_DATA: "Any Data",
    GEOFENCE_OUT: "Outside Geofence",
    GEOFENCE_IN: "Inside Geofence",
    GEORADIUS_OUT: "Outside Geo-Radius",
    GEORADIUS_IN: "Inside Geo-Radius"
  }

  # Other Constants
  DISABLED = -1
  ANY = -2

  # Periods
  SECOND = 1
  MINUTE = 2
  HOUR = 3
  DAY = 4
  WEEK = 5
  MONTH = 6

class RECORD():
    # Data Types
    DATA_TYPES = ['string', 'number', 'boolean', 'date', 'datetime', 'timeofday', 'latlng']  # From Google Visualization API (added latlng)

    ILLEGAL_COLNAMES = ["enterprise","sensor","target","dt_created","dt_recorded","minute","hour"]

# Message channels
class CHANNEL():
  EMAIL = 1
  SMS = 2
  GCM = 3 # Google cloud message (push)

class PAYMENT():
    # For incentives

    # Channels
    AIRTIME = 1
    MOBILE_MONEY = 2

    # Directions
    TO = 1
    FROM = 2

    # Statuses
    REQUESTED = 1
    SENT = 2
    CONFIRMED = 3
    FAILED = 4

    CHANNEL_LABELS = {AIRTIME: "Airtime", MOBILE_MONEY: "Mobile Money"}
    STATUS_LABELS = {REQUESTED: "Requested", SENT: "Sent", CONFIRMED: "Confirmed", FAILED: "Failed"}
    DIRECTION_LABELS = {TO: "To", FROM: "From"}

class UI():

  # UI Message Levels
  INFO = 0
  SUCCESS = 1
  ERROR = 2


class ERROR():
  OK = 0
  UNAUTHORIZED = 1
  BAD_TOKEN = 2
  USER_NOT_FOUND = 3
  MALFORMED = 4
  AUTH_FAILED = 5
  SENSOR_NOT_FOUND = 6

  OTHER = 99

  LABELS = {OK: "OK", UNAUTHORIZED: "Unauthorized", BAD_TOKEN: "Bad Token", USER_NOT_FOUND: "User not found", MALFORMED: "Malformed Request!", AUTH_FAILED: "Auth failed"}

class USER():
    LIMITED_READ = 1
    LIMITED_READ_WRITE = 2
    ACCOUNT_ADMIN = 3
    ADMIN = 4

    LABELS = {LIMITED_READ: "Limited (Read Only)", LIMITED_READ_WRITE: "Limited", ACCOUNT_ADMIN: "Account Admin", ADMIN: "Admin"}

# Memcache keys and prefixes
MC_EXPORT_STATUS = "MC_EXPORT_STATUS_%s"

NBO_LAT = -1.274359
NBO_LON = 36.813106
NBO_LOC = "%s,%s" % (NBO_LAT, NBO_LON)

COUNTRIES = [
    ("US","United States"),
    ("AF","Afghanistan"),
    ("AX","Aland Islands"),
    ("AL","Albania"),
    ("DZ","Algeria"),
    ("AS","American Samoa"),
    ("AD","Andorra"),
    ("AO","Angola"),
    ("AI","Anguilla"),
    ("AQ","Antarctica"),
    ("AG","Antigua and Barbuda"),
    ("AR","Argentina"),
    ("AM","Armenia"),
    ("AW","Aruba"),
    ("AU","Australia"),
    ("AT","Austria"),
    ("AZ","Azerbaijan"),
    ("BS","Bahamas"),
    ("BH","Bahrain"),
    ("BD","Bangladesh"),
    ("BB","Barbados"),
    ("BY","Belarus"),
    ("BE","Belgium"),
    ("BZ","Belize"),
    ("BJ","Benin"),
    ("BM","Bermuda"),
    ("BT","Bhutan"),
    ("BO","Bolivia, Plurinational State of"),
    ("BQ","Bonaire, Sint Eustatius and Saba"),
    ("BA","Bosnia and Herzegovina"),
    ("BW","Botswana"),
    ("BV","Bouvet Island"),
    ("BR","Brazil"),
    ("IO","British Indian Ocean Territory"),
    ("BN","Brunei Darussalam"),
    ("BG","Bulgaria"),
    ("BF","Burkina Faso"),
    ("BI","Burundi"),
    ("KH","Cambodia"),
    ("CM","Cameroon"),
    ("CA","Canada"),
    ("CV","Cape Verde"),
    ("KY","Cayman Islands"),
    ("CF","Central African Republic"),
    ("TD","Chad"),
    ("CL","Chile"),
    ("CN","China"),
    ("CX","Christmas Island"),
    ("CC","Cocos (Keeling) Islands"),
    ("CO","Colombia"),
    ("KM","Comoros"),
    ("CG","Congo"),
    ("CD","Congo, the Democratic Republic of the"),
    ("CK","Cook Islands"),
    ("CR","Costa Rica"),
    ("CI","Cote d'Ivoire"),
    ("HR","Croatia"),
    ("CU","Cuba"),
    ("CW","Curacao"),
    ("CY","Cyprus"),
    ("CZ","Czech Republic"),
    ("DK","Denmark"),
    ("DJ","Djibouti"),
    ("DM","Dominica"),
    ("DO","Dominican Republic"),
    ("EC","Ecuador"),
    ("EG","Egypt"),
    ("SV","El Salvador"),
    ("GQ","Equatorial Guinea"),
    ("ER","Eritrea"),
    ("EE","Estonia"),
    ("ET","Ethiopia"),
    ("FK","Falkland Islands (Malvinas)"),
    ("FO","Faroe Islands"),
    ("FJ","Fiji"),
    ("FI","Finland"),
    ("FR","France"),
    ("GF","French Guiana"),
    ("PF","French Polynesia"),
    ("TF","French Southern Territories"),
    ("GA","Gabon"),
    ("GM","Gambia"),
    ("GE","Georgia"),
    ("DE","Germany"),
    ("GH","Ghana"),
    ("GI","Gibraltar"),
    ("GR","Greece"),
    ("GL","Greenland"),
    ("GD","Grenada"),
    ("GP","Guadeloupe"),
    ("GU","Guam"),
    ("GT","Guatemala"),
    ("GG","Guernsey"),
    ("GN","Guinea"),
    ("GW","Guinea-Bissau"),
    ("GY","Guyana"),
    ("HT","Haiti"),
    ("HM","Heard Island and McDonald Islands"),
    ("VA","Holy See (Vatican City State)"),
    ("HN","Honduras"),
    ("HK","Hong Kong"),
    ("HU","Hungary"),
    ("IS","Iceland"),
    ("IN","India"),
    ("ID","Indonesia"),
    ("IR","Iran, Islamic Republic of"),
    ("IQ","Iraq"),
    ("IE","Ireland"),
    ("IM","Isle of Man"),
    ("IL","Israel"),
    ("IT","Italy"),
    ("JM","Jamaica"),
    ("JP","Japan"),
    ("JE","Jersey"),
    ("JO","Jordan"),
    ("KZ","Kazakhstan"),
    ("KE","Kenya"),
    ("KI","Kiribati"),
    ("KP","Korea, Democratic People's Republic of"),
    ("KR","Korea, Republic of"),
    ("KW","Kuwait"),
    ("KG","Kyrgyzstan"),
    ("LA","Lao People's Democratic Republic"),
    ("LV","Latvia"),
    ("LB","Lebanon"),
    ("LS","Lesotho"),
    ("LR","Liberia"),
    ("LY","Libya"),
    ("LI","Liechtenstein"),
    ("LT","Lithuania"),
    ("LU","Luxembourg"),
    ("MO","Macao"),
    ("MK","Macedonia, the former Yugoslav Republic of"),
    ("MG","Madagascar"),
    ("MW","Malawi"),
    ("MY","Malaysia"),
    ("MV","Maldives"),
    ("ML","Mali"),
    ("MT","Malta"),
    ("MH","Marshall Islands"),
    ("MQ","Martinique"),
    ("MR","Mauritania"),
    ("MU","Mauritius"),
    ("YT","Mayotte"),
    ("MX","Mexico"),
    ("FM","Micronesia, Federated States of"),
    ("MD","Moldova, Republic of"),
    ("MC","Monaco"),
    ("MN","Mongolia"),
    ("ME","Montenegro"),
    ("MS","Montserrat"),
    ("MA","Morocco"),
    ("MZ","Mozambique"),
    ("MM","Myanmar"),
    ("NA","Namibia"),
    ("NR","Nauru"),
    ("NP","Nepal"),
    ("NL","Netherlands"),
    ("NC","New Caledonia"),
    ("NZ","New Zealand"),
    ("NI","Nicaragua"),
    ("NE","Niger"),
    ("NG","Nigeria"),
    ("NU","Niue"),
    ("NF","Norfolk Island"),
    ("MP","Northern Mariana Islands"),
    ("NO","Norway"),
    ("OM","Oman"),
    ("PK","Pakistan"),
    ("PW","Palau"),
    ("PS","Palestinian Territory, Occupied"),
    ("PA","Panama"),
    ("PG","Papua New Guinea"),
    ("PY","Paraguay"),
    ("PE","Peru"),
    ("PH","Philippines"),
    ("PN","Pitcairn"),
    ("PL","Poland"),
    ("PT","Portugal"),
    ("PR","Puerto Rico"),
    ("QA","Qatar"),
    ("RE","Reunion"),
    ("RO","Romania"),
    ("RU","Russian Federation"),
    ("RW","Rwanda"),
    ("BL","Saint Barthelemy"),
    ("SH","Saint Helena, Ascension and Tristan da Cunha"),
    ("KN","Saint Kitts and Nevis"),
    ("LC","Saint Lucia"),
    ("MF","Saint Martin (French part)"),
    ("PM","Saint Pierre and Miquelon"),
    ("VC","Saint Vincent and the Grenadines"),
    ("WS","Samoa"),
    ("SM","San Marino"),
    ("ST","Sao Tome and Principe"),
    ("SA","Saudi Arabia"),
    ("SN","Senegal"),
    ("RS","Serbia"),
    ("SC","Seychelles"),
    ("SL","Sierra Leone"),
    ("SG","Singapore"),
    ("SX","Sint Maarten (Dutch part)"),
    ("SK","Slovakia"),
    ("SI","Slovenia"),
    ("SB","Solomon Islands"),
    ("SO","Somalia"),
    ("ZA","South Africa"),
    ("GS","South Georgia and the South Sandwich Islands"),
    ("SS","South Sudan"),
    ("ES","Spain"),
    ("LK","Sri Lanka"),
    ("SD","Sudan"),
    ("SR","Suriname"),
    ("SJ","Svalbard and Jan Mayen"),
    ("SZ","Swaziland"),
    ("SE","Sweden"),
    ("CH","Switzerland"),
    ("SY","Syrian Arab Republic"),
    ("TW","Taiwan, Province of China"),
    ("TJ","Tajikistan"),
    ("TZ","Tanzania, United Republic of"),
    ("TH","Thailand"),
    ("TL","Timor-Leste"),
    ("TG","Togo"),
    ("TK","Tokelau"),
    ("TO","Tonga"),
    ("TT","Trinidad and Tobago"),
    ("TN","Tunisia"),
    ("TR","Turkey"),
    ("TM","Turkmenistan"),
    ("TC","Turks and Caicos Islands"),
    ("TV","Tuvalu"),
    ("UG","Uganda"),
    ("UA","Ukraine"),
    ("AE","United Arab Emirates"),
    ("GB","United Kingdom"),
    ("UM","United States Minor Outlying Islands"),
    ("UY","Uruguay"),
    ("UZ","Uzbekistan"),
    ("VU","Vanuatu"),
    ("VE","Venezuela, Bolivarian Republic of"),
    ("VN","Viet Nam"),
    ("VG","Virgin Islands, British"),
    ("VI","Virgin Islands, U.S."),
    ("WF","Wallis and Futuna"),
    ("EH","Western Sahara"),
    ("YE","Yemen"),
    ("ZM","Zambia"),
    ("ZW","Zimbabwe")
]