from google.appengine.ext import db, deferred, blobstore
from google.appengine.api import mail, images, urlfetch, memcache
import os

from datetime import datetime,timedelta

import tools
import authorized
import logging
from models import *
from constants import *
import handlers
import json

# Google OAuth

def GetGoogleKeyCerts():
    d = memcache.get(MC_GOOGLE_KEY_CERT_DICT)
    if not d:
        d = UpdateGoogleKeyCerts()
    else:
        logging.debug("Got Google Key Certs")
    return d

def UpdateGoogleKeyCerts():
    url = "https://www.googleapis.com/oauth2/v1/certs"
    result = urlfetch.fetch(url, deadline=15)
    if result.status_code == 200:
        try:
            response = json.loads(result.content)
            logging.debug("Updated Key Certs from Google! %s" % response.keys())
            memcache.set(MC_GOOGLE_KEY_CERT_DICT, response, 6*60*60) # 6 hours TODO: Handle expire!
            return response
        except Exception, e:
            logging.error("Error decoding key certs: %s" % result.content)
    return None

def VerifyGoogleJWT(token, iss="accounts.google.com", aud=TOKEN_AUD, azp=TOKEN_AZP, email=None):
    # NOTE: Unimplemented
    return True
