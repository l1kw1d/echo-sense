import logging
from google.appengine.ext import webapp, db, deferred
from google.appengine.api import users, images, memcache, taskqueue
from google.appengine.ext.webapp import template
import handlers
from errors import Shutdown


def shutdown():
    raise Shutdown()


class WarmupHandler(handlers.BaseRequestHandler):
    def get(self):
        logging.info("Warmup Request")


class StartInstance(handlers.BaseRequestHandler):
    def get(self):
        logging.info("Instance start request")
        from google.appengine.api import runtime
        runtime.set_shutdown_hook(shutdown)

