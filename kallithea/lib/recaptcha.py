# -*- coding: utf-8 -*-
import urllib
import urllib2

API_SSL_SERVER = "https://www.google.com/recaptcha/api"
API_SERVER = "http://www.google.com/recaptcha/api"
VERIFY_SERVER = "www.google.com"


class RecaptchaResponse(object):
    def __init__(self, is_valid, error_code=None):
        self.is_valid = is_valid
        self.error_code = error_code

    def __repr__(self):
        return '<RecaptchaResponse:%s>' % (self.is_valid)


def submit(recaptcha_challenge_field, recaptcha_response_field, private_key,
           remoteip):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse
    for the request

    recaptcha_challenge_field -- The value of recaptcha_challenge_field from the form
    recaptcha_response_field -- The value of recaptcha_response_field from the form
    private_key -- your reCAPTCHA private key
    remoteip -- the user's IP address
    """

    if not (recaptcha_response_field and recaptcha_challenge_field and
                len(recaptcha_response_field) and len(
            recaptcha_challenge_field)):
        return RecaptchaResponse(is_valid=False,
                                 error_code='incorrect-captcha-sol')

    def encode_if_necessary(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    params = urllib.urlencode({
        'privatekey': encode_if_necessary(private_key),
        'remoteip': encode_if_necessary(remoteip),
        'challenge': encode_if_necessary(recaptcha_challenge_field),
        'response': encode_if_necessary(recaptcha_response_field),
    })

    req = urllib2.Request(
        url="http://%s/recaptcha/api/verify" % VERIFY_SERVER,
        data=params,
        headers={
            "Content-type": "application/x-www-form-urlencoded",
            "User-agent": "reCAPTCHA Python"
        }
    )

    httpresp = urllib2.urlopen(req)

    return_values = httpresp.read().splitlines()
    httpresp.close()

    return_code = return_values[0]

    if return_code == "true":
        return RecaptchaResponse(is_valid=True)
    else:
        return RecaptchaResponse(is_valid=False, error_code=return_values[1])
