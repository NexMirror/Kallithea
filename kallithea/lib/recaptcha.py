# -*- coding: utf-8 -*-
import json
import urllib
import urllib2


class RecaptchaResponse(object):
    def __init__(self, is_valid, error_code=None):
        self.is_valid = is_valid
        self.error_code = error_code

    def __repr__(self):
        return '<RecaptchaResponse:%s>' % (self.is_valid)


def submit(g_recaptcha_response, private_key, remoteip):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse for the request

    g_recaptcha_response -- The value of g_recaptcha_response from the form
    private_key -- your reCAPTCHA private key
    remoteip -- the user's IP address
    """

    if not (g_recaptcha_response and len(g_recaptcha_response)):
        return RecaptchaResponse(is_valid=False, error_code='incorrect-captcha-sol')

    def encode_if_necessary(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    params = urllib.urlencode({
        'secret': encode_if_necessary(private_key),
        'remoteip': encode_if_necessary(remoteip),
        'response': encode_if_necessary(g_recaptcha_response),
    })

    req = urllib2.Request(
        url="https://www.google.com/recaptcha/api/siteverify",
        data=params,
        headers={
            "Content-type": "application/x-www-form-urlencoded",
            "User-agent": "reCAPTCHA Python"
        }
    )

    httpresp = urllib2.urlopen(req)
    return_values = json.loads(httpresp.read())
    httpresp.close()

    if not (isinstance(return_values, dict)):
        return RecaptchaResponse(is_valid=False, error_code='incorrect-captcha-sol')
    elif (("success" in return_values) and ((return_values["success"] is True) or (return_values["success"] == "true"))):
        return RecaptchaResponse(is_valid=True)
    elif (("error-codes" in return_values) and isinstance(return_values["error-codes"], list) and (len(return_values["error-codes"]) > 0)):
        return RecaptchaResponse(is_valid=False, error_code=return_values["error-codes"][0])
    else:
        return RecaptchaResponse(is_valid=False, error_code='incorrect-captcha-sol')
