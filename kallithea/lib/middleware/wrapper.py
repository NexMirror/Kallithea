# -*- coding: utf-8 -*-
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
"""
kallithea.lib.middleware.wrapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wrap app to measure request and response time ... until the response starts.

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 23, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import time

from kallithea.lib.base import _get_access_path, _get_ip_addr
from kallithea.lib.utils2 import safe_unicode


log = logging.getLogger(__name__)


class Meter:

    def __init__(self):
        self._start = time.time()

    def duration(self):
        return time.time() - self._start


class RequestWrapper(object):

    def __init__(self, app, config):
        self.application = app
        self.config = config

    def __call__(self, environ, start_response):
        meter = Meter()
        description = "Request from %s for %s" % (
            _get_ip_addr(environ),
            safe_unicode(_get_access_path(environ)),
        )
        try:
            result = self.application(environ, start_response)
        finally:
            log.info("%s responding after %.3fs", description, meter.duration())
        return result
