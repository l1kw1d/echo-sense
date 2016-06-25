import os, logging
import webapp2

from actions import actions, adminActions, cronActions, schemaActions, gcmActions
import tasks
from views import views
import settings
import api, inbox

SECS_PER_WEEK = 60 * 60 * 24 * 7
# Enable ctypes -> Jinja2 tracebacks
PRODUCTION_MODE = not os.environ.get(
    'SERVER_SOFTWARE', 'Development').startswith('Development')

ROOT_DIRECTORY = os.path.dirname(__file__)

if not PRODUCTION_MODE:
      from google.appengine.tools.devappserver2.python import sandbox
      sandbox._WHITE_LIST_C_MODULES += ['_ctypes', 'gestalt']
      TEMPLATE_DIRECTORY = os.path.join(ROOT_DIRECTORY, 'src')
else:
      TEMPLATE_DIRECTORY = os.path.join(ROOT_DIRECTORY, 'dist')

curr_path = os.path.abspath(os.path.dirname(__file__))



config = {
      'webapp2_extras.sessions': {
            'secret_key': settings.COOKIE_KEY,
            'session_max_age': SECS_PER_WEEK,
            'cookie_args': {'max_age': SECS_PER_WEEK},
            'cookie_name': 'echo_sense_session'
      },
      'webapp2_extras.jinja2': {
            'template_path': TEMPLATE_DIRECTORY
    }
}

app = webapp2.WSGIApplication(
     [
      webapp2.Route('/invite', handler=views.Invite, name="vInvite"),
      webapp2.Route('/users/<id>', handler=views.UserDetail, name="vUserDetail"),

      # Admin Actions
      webapp2.Route('/admin/gauth/install', handler=adminActions.Install, name="adminInstall"),
      webapp2.Route('/admin/actions/clean_delete/<key>', handler=adminActions.CleanDelete, name="CleanDelete"),
      webapp2.Route('/admin/actions/users/create', handler=adminActions.CreateUser, name="aCreateCustomer"),
      webapp2.Route('/admin/actions/gcm/manual', handler=adminActions.ManualGCM, name="ManualGCM"),
      webapp2.Route('/admin/actions/users/<ukey>/logout', handler=adminActions.LogoutUser, name="LogoutUser"),

      # API - Auth
      webapp2.Route('/api/login', handler=api.Login, name="apiLogin"),
      webapp2.Route('/api/logout', handler=api.Logout, name="apiLogout"),

      # API - Client
      webapp2.Route('/api/public/enterprise_lookup/<key_or_alias>', handler=api.PublicAPI, handler_method="enterprise_lookup", methods=["GET"]),
      webapp2.Route('/api/public/forgot_password/<email_or_phone>', handler=api.PublicAPI, handler_method="forgot_password", methods=["POST"]),
      webapp2.Route('/api/invite/invite', handler=api.InviteAPI, handler_method="invite", methods=["POST"]),
      webapp2.Route('/api/enterprise', handler=api.EnterpriseAPI, handler_method="list", methods=["GET"]),
      webapp2.Route('/api/enterprise', handler=api.EnterpriseAPI, handler_method="update", methods=["POST"]),
      webapp2.Route('/api/enterprise/delete', handler=api.EnterpriseAPI, handler_method="delete", methods=["POST"]),
      webapp2.Route('/api/enterprise/<key_or_alias>', handler=api.EnterpriseAPI, handler_method="detail", methods=["GET"]),
      webapp2.Route('/api/sensor', handler=api.SensorAPI, handler_method="list", methods=["GET"], name="SensorAPI"),
      webapp2.Route('/api/sensor', handler=api.SensorAPI, handler_method="update", methods=["POST"], name="SensorAPI"),
      webapp2.Route('/api/sensor/delete', handler=api.SensorAPI, handler_method="delete", methods=["POST"], name="SensorAPI"),
      webapp2.Route('/api/sensor/<kn>', handler=api.SensorAPI, handler_method="detail", methods=["GET"], name="SensorAPI"),
      webapp2.Route('/api/sensor/<kn>/action/<action>', handler=api.SensorAPI, handler_method="action", methods=["POST"], name="SensorAPI"),
      webapp2.Route('/api/data', handler=api.DataAPI, handler_method="list", methods=["GET"], name="DataAPI"),
      webapp2.Route('/api/data/<sensor_kn>/<kn>', handler=api.DataAPI, handler_method="detail", methods=["GET"], name="DataAPI"),
      webapp2.Route('/api/analysis', handler=api.AnalysisAPI, handler_method="list", methods=["GET"], name="AnalysisAPI"),
      webapp2.Route('/api/analysis/<akn>', handler=api.AnalysisAPI, handler_method="detail", methods=["GET"], name="AnalysisAPI"),
      webapp2.Route('/api/alarm', handler=api.AlarmAPI, handler_method="list", methods=["GET"], name="AlarmAPI"),
      webapp2.Route('/api/alarm/<skn>/<aid>', handler=api.AlarmAPI, handler_method="detail", methods=["GET"], name="AlarmAPI"),
      webapp2.Route('/api/rule', handler=api.RuleAPI, handler_method="list", methods=["GET"], name="RuleAPI"),
      webapp2.Route('/api/rule', handler=api.RuleAPI, handler_method="update", methods=["POST"], name="RuleAPI"),
      webapp2.Route('/api/rule/delete', handler=api.RuleAPI, handler_method="delete", methods=["POST"], name="RuleAPI"),
      webapp2.Route('/api/rule/<skey>', handler=api.RuleAPI, handler_method="detail", methods=["GET"], name="RuleAPI"),
      webapp2.Route('/api/sensorprocesstask', handler=api.SensorProcessTaskAPI, handler_method="list", methods=["GET"], name="SensorProcessTaskAPI"),
      webapp2.Route('/api/sensorprocesstask/delete', handler=api.SensorProcessTaskAPI, handler_method="delete", methods=["POST"], name="SensorProcessTaskAPI"),
      webapp2.Route('/api/processtask', handler=api.ProcessTaskAPI, handler_method="list", methods=["GET"], name="ProcessTaskAPI"),
      webapp2.Route('/api/processtask', handler=api.ProcessTaskAPI, handler_method="update", methods=["POST"], name="ProcessTaskAPI"),
      webapp2.Route('/api/processtask/delete', handler=api.ProcessTaskAPI, handler_method="delete", methods=["POST"], name="ProcessTaskAPI"),
      webapp2.Route('/api/processtask/associate', handler=api.ProcessTaskAPI, handler_method="associate", methods=["POST"], name="ProcessTaskAPI"),
      webapp2.Route('/api/processtask/duplicate', handler=api.ProcessTaskAPI, handler_method="duplicate", methods=["POST"], name="ProcessTaskAPI"),
      webapp2.Route('/api/processtask/run', handler=api.ProcessTaskAPI, handler_method="run", methods=["POST"], name="ProcessTaskAPI"),
      webapp2.Route('/api/processtask/<key_or_id>', handler=api.ProcessTaskAPI, handler_method="detail", methods=["GET"], name="ProcessTaskAPI"),
      webapp2.Route('/api/sensor/media/upload', handler=api.UploadMedia, name="UploadMedia", methods=["POST"]),
      webapp2.Route('/api/sensortype', handler=api.SensorTypeAPI, handler_method="list", methods=["GET"], name="SensorTypeAPI"),
      webapp2.Route('/api/sensortype', handler=api.SensorTypeAPI, handler_method="update", methods=["POST"], name="SensorTypeAPI"),
      webapp2.Route('/api/sensortype/create', handler=api.SensorTypeAPI, handler_method="create", methods=["POST"], name="SensorTypeAPI"),
      webapp2.Route('/api/sensortype/delete', handler=api.SensorTypeAPI, handler_method="delete", methods=["POST"], name="SensorTypeAPI"),
      webapp2.Route('/api/sensortype/<id>', handler=api.SensorTypeAPI, handler_method="detail", methods=["GET"], name="SensorTypeAPI"),
      webapp2.Route('/api/group', handler=api.GroupAPI, handler_method="list", methods=["GET"], name="GroupAPI"),
      webapp2.Route('/api/group', handler=api.GroupAPI, handler_method="update", methods=["POST"], name="GroupAPI"),
      webapp2.Route('/api/group/delete', handler=api.GroupAPI, handler_method="delete", methods=["POST"], name="GroupAPI"),
      webapp2.Route('/api/group/<id>', handler=api.GroupAPI, handler_method="detail", methods=["GET"], name="GroupAPI"),
      webapp2.Route('/api/target', handler=api.TargetAPI, handler_method="list", methods=["GET"], name="TargetAPI"),
      webapp2.Route('/api/target', handler=api.TargetAPI, handler_method="update", methods=["POST"], name="TargetAPI"),
      webapp2.Route('/api/target/delete', handler=api.TargetAPI, handler_method="delete", methods=["POST"], name="TargetAPI"),
      webapp2.Route('/api/target/<id>', handler=api.TargetAPI, handler_method="detail", methods=["GET"], name="TargetAPI"),
      webapp2.Route('/api/user', handler=api.UserAPI, handler_method="list", methods=["GET"], name="UserAPI"),
      webapp2.Route('/api/user', handler=api.UserAPI, handler_method="update", methods=["POST"], name="UserAPI"),
      webapp2.Route('/api/user/delete', handler=api.UserAPI, handler_method="delete", methods=["POST"], name="UserAPI"),
      webapp2.Route('/api/user/photo/upload', handler=api.UploadProfilePhoto, methods=["POST"]),
      webapp2.Route('/api/report', handler=api.ReportAPI, handler_method="list", methods=["GET"]),
      webapp2.Route('/api/report/generate', handler=api.ReportAPI, handler_method="generate", methods=["POST"]),
      webapp2.Route('/api/report/serve', handler=api.ReportAPI, handler_method="serve", methods=["GET"]),
      webapp2.Route('/api/report/delete', handler=api.ReportAPI, handler_method="delete", methods=["POST"]),
      webapp2.Route('/api/apilog', handler=api.APILogAPI, handler_method="list", methods=["GET"]),
      webapp2.Route('/api/payment', handler=api.PaymentAPI, handler_method="list", methods=["GET"]),
      webapp2.Route('/api/upload/get_url', handler=api.GetUploadUrl, name="apiGetUploadUrl"),
      webapp2.Route('/api/search', handler=api.SearchAPI, handler_method="search", name="SearchAPI", methods=["GET"]),
      webapp2.Route('/api/search/delete/<doc_key>', handler=api.SearchAPI, handler_method="delete_doc", name="SearchAPI", methods=["GET"]),

      # Communications
      webapp2.Route('/api/email/send', handler=api.SendEmail, name="apiSendEmail"),

      # Inbox
      webapp2.Route('/<eid>/inbox/<format>/<sensor_kn>', handler=inbox.DataInbox, name="DataInbox"),

      # Tasks
      # webapp2.Route('/tasks/processtask/run', handler=tasks.RunProcessTask),

      # Misc
      webapp2.Route('/res/<bk>', handler=views.ServeBlob, name="ServeBlob"),
      webapp2.Route('/_ah/warmup', handler=actions.WarmupHandler),

      # GCM
      webapp2.Route('/gcm/connect', gcmActions.GCMConnection),
      # webapp2.Route('/gae_python_gcm/send_request', gcmActions.SendMessage),

      # Cron jobs (see cron.yaml)
      webapp2.Route('/cron/monthly', handler=cronActions.Monthly),
      webapp2.Route('/cron/digests/admin', handler=cronActions.AdminDigest),
      webapp2.Route('/cron/oauth/google_key_certs', handler=adminActions.UpdateGoogleKeyCerts),

      webapp2.Route(r'/<:.*>', handler=views.EchoSenseApp, name="EchoSenseApp"),


      ], debug=True,
    config=config)
