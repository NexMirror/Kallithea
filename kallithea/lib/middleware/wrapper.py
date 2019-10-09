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

Wrap app to measure request and response time ... all the way to the response
WSGI iterator has been closed.

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

    def __init__(self, start_response):
        self._start_response = start_response
        self._start = time.time()
        self._size = 0

    def duration(self):
        return time.time() - self._start

    def start_response(self, status, response_headers, exc_info=None):
        write = self._start_response(status, response_headers, exc_info)
        def metered_write(s):
            self.measure(s)
            write(s)
        return metered_write

    def measure(self, chunk):
        self._size += len(chunk)

    def size(self):
        return self._size


class ResultIter:

    def __init__(self, result, meter, description):
        self._result_close = getattr(result, 'close', None) or (lambda: None)
        self._next = iter(result).next
        self._meter = meter
        self._description = description

    def __iter__(self):
        return self

    def next(self):
        chunk = self._next()
        self._meter.measure(chunk)
        return chunk

    def close(self):
        self._result_close()
        log.info("%s responded after %.3fs with %s bytes", self._description, self._meter.duration(), self._meter.size())


class RequestWrapper(object):

    def __init__(self, app, config):
        self.application = app
        self.config = config

    def __call__(self, environ, start_response):
        meter = Meter(start_response)
        description = "Request from %s for %s" % (
            _get_ip_addr(environ),
            safe_unicode(_get_access_path(environ)),
        )
        try:
            result = self.application(environ, meter.start_response)
        finally:
            log.info("%s responding after %.3fs", description, meter.duration())
        return ResultIter(result, meter, description)
