# -*- coding: utf-8 -*-
"""
    rhodecode.lib.middleware.https_fixup
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    middleware to handle https correctly

    :created_on: May 23, 2010
    :author: marcink
    :copyright: (C) 2010-2012 Marcin Kuzminski <marcin@python-works.com>
    :license: GPLv3, see COPYING for more details.
"""
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pylons.controllers.util import Request
from rhodecode.lib.utils2 import str2bool


class HttpsFixup(object):

    def __init__(self, app, config):
        self.application = app
        self.config = config

    def __call__(self, environ, start_response):
        self.__fixup(environ)
        debug = str2bool(self.config.get('debug'))
        if str2bool(self.config.get('use_htsts')) and not debug:
            req = Request(environ, self.application)
            resp = req.get_response(self.application)
            if environ['wsgi.url_scheme'] == 'https':
                resp.headers['Strict-Transport-Security'] = \
                    'max-age=8640000; includeSubDomains'
            return resp(environ, start_response)

        return self.application(environ, start_response)

    def __fixup(self, environ):
        """
        Function to fixup the environ as needed. In order to use this
        middleware you should set this header inside your
        proxy ie. nginx, apache etc.
        """
        # DETECT PROTOCOL !
        if 'HTTP_X_URL_SCHEME' in environ:
            proto = environ.get('HTTP_X_URL_SCHEME')
        elif 'HTTP_X_FORWARDED_SCHEME' in environ:
            proto = environ.get('HTTP_X_FORWARDED_SCHEME')
        elif 'HTTP_X_FORWARDED_PROTO' in environ:
            proto = environ.get('HTTP_X_FORWARDED_PROTO')
        else:
            proto = 'http'
        org_proto = proto

        # if we have force, just override
        if str2bool(self.config.get('force_https')):
            proto = 'https'

        environ['wsgi.url_scheme'] = proto
        environ['wsgi._org_proto'] = org_proto
