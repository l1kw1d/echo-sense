from datetime import datetime, timedelta, date
from google.appengine.ext import db, deferred
from google.appengine.api import mail, taskqueue, urlfetch
import urllib
import tools
import json
import logging
import random
from constants import *
from gae_python_gcm.gcm import GCMMessage, GCMConnection

def send_gcm_message(payload, users=None, collapse=None):
    if not users:
        users = []
    tokens = [u.gcm_reg_id for u in users if u and u.gcm_reg_id]
    if len(tokens):
        gcm_message = GCMMessage(tokens, payload, collapse_key=collapse)
        gcm_conn = GCMConnection()
        gcm_conn.notify_device(gcm_message)
    else:
        logging.debug("No GCM connected devices - Not sending GCM message.")

def send_email(to, subject, body, signoff=None):
    if to:
        logging.info("Sending email to %s" % (to))
        subject = EMAIL_PREFIX + subject
        subject = tools.truncate(subject, 40)
        if signoff:
            body = body + signoff
        deferred.defer(mail.send_mail, to=to, sender=SENDER_EMAIL, subject=subject, body=body)

def email_admins(subject, body):
    send_email(NOTIF_EMAILS, subject, body)

def send_sms(enterprise, phone, message):
    logging.info("Sending SMS to %s" % (phone))
    AT_USERNAME = enterprise.get_gateway_property('atalking', 'username')
    AT_FROM_SHORTCODE = enterprise.get_gateway_property('atalking', 'shortcode')
    AT_API_KEY = enterprise.get_gateway_property('atalking', 'ApiKey')
    if not tools.on_dev_server() and (AT_USERNAME and AT_FROM_SHORTCODE and AT_API_KEY):
        url = "http://api.africastalking.com/version1/messaging"
        enc = urllib.urlencode([
            ('username', AT_USERNAME),
            ('to', '+' + phone),
            ('from', AT_FROM_SHORTCODE),
            ('message', message),
            ('bulkSMSMode', 1),
            ('enqueue', 1)
        ])
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': "application/json",
            'ApiKey': AT_API_KEY
        }
        response = urlfetch.fetch(url=url, payload=enc, method="POST", deadline=60, headers=headers)
        if response.status_code == 200:
            logging.debug(response.content)

def send_message(user, message, **additional_params):
    logging.info("Trying to send message to %s: %s" % (user, message))
    if user.alert_channel == CHANNEL.SMS and user.phone:
        phone = tools.standardize_phone(user.phone)
        if phone:
            send_sms(user.enterprise, phone, message)
    elif user.alert_channel == CHANNEL.EMAIL and user.email:
        send_email(user.email, message, message, signoff="\n\n-Echo Sense")
    elif user.alert_channel == CHANNEL.GCM and user.gcm_reg_id:
        payload = {"message": message}
        if additional_params:
            payload.update(additional_params)
        send_gcm_message(payload, users=[user])

def send_airtime(enterprise, phone, amount, currency):
    """
    Takes a payment object and requests airtime via Africa's Talking

    Example response:
    [
     {
      "errorMessage":"None",
      "phoneNumber":"2547XXYYZZZZ",
      "amount":"KES 100",
      "status":"sent",
      "requestId":"ATQid_4fbec14b3c6b976d398957f9f8a65b3d"
     }
    ]
    """
    AT_API_KEY = enterprise.get_gateway_property('atalking', 'ApiKey')
    amount_str = "[{\"phoneNumber\":\"+%s\",\"amount\":\"%s %d\"}]" % (phone, currency, int(amount))
    par_list=[
        ('ApiKey',AT_API_KEY),
        ('username',"echomobile"),
        ('recipients', amount_str)
    ]
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': "application/json",
        'ApiKey': AT_API_KEY
    }
    base_url="http://api.africastalking.com/version1/airtime/send"
    enc = urllib.urlencode(par_list)
    dry = "DRY" if tools.on_dev_server() else "REAL"
    logging.debug("Making %s request: %s" % (dry, base_url + '?' + enc))
    gateway_text_response = gateway_id = None
    success = False
    if tools.on_dev_server():
        success = True
        gateway_text_response = "Dev server, Auto-success"
        gateway_id = str(random.randint(1,99999))
    else:
        try:
            response = urlfetch.fetch(url=base_url, payload=enc, method="POST", deadline=60, headers=headers)
            resp_content = None
            if response.status_code in [200, 201]:
                resp_content = json.loads(response.content)
                if resp_content and resp_content.has_key('responses'):
                    resps = resp_content.get('responses')
                    if len(resps):
                        oresp = resps[0]
                        if oresp.has_key('status') and oresp['status'].upper().strip() == 'SENT':
                            gateway_id = oresp.get('requestId')
                            success = True
        except Exception, e:
            pass
    return (success, gateway_text_response, gateway_id)