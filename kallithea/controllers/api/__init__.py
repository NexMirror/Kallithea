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
kallithea.controllers.api
~~~~~~~~~~~~~~~~~~~~~~~~~

JSON RPC controller

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Aug 20, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import inspect
import itertools
import logging
import time
import traceback
import types

from tg import Response, TGController, request, response
from webob.exc import HTTPError, HTTPException

from kallithea.lib.auth import AuthUser
from kallithea.lib.base import _get_access_path
from kallithea.lib.base import _get_ip_addr as _get_ip
from kallithea.lib.compat import json
from kallithea.lib.utils2 import safe_str, safe_unicode
from kallithea.model.db import User


log = logging.getLogger('JSONRPC')


class JSONRPCError(BaseException):

    def __init__(self, message):
        self.message = message
        super(JSONRPCError, self).__init__()

    def __str__(self):
        return safe_str(self.message)


class JSONRPCErrorResponse(Response, HTTPException):
    """
    Generate a Response object with a JSON-RPC error body
    """

    def __init__(self, message=None, retid=None, code=None):
        HTTPException.__init__(self, message, self)
        Response.__init__(self,
                          json_body=dict(id=retid, result=None, error=message),
                          status=code,
                          content_type='application/json')


class JSONRPCController(TGController):
    """
     A WSGI-speaking JSON-RPC controller class

     See the specification:
     <http://json-rpc.org/wiki/specification>`.

     Valid controller return values should be json-serializable objects.

     Sub-classes should catch their exceptions and raise JSONRPCError
     if they want to pass meaningful errors to the client.

     """

    def _get_ip_addr(self, environ):
        return _get_ip(environ)

    def _get_method_args(self):
        """
        Return `self._rpc_args` to dispatched controller method
        chosen by __call__
        """
        return self._rpc_args

    def _dispatch(self, state, remainder=None):
        """
        Parse the request body as JSON, look up the method on the
        controller and if it exists, dispatch to it.
        """
        # Since we are here we should respond as JSON
        response.content_type = 'application/json'

        environ = state.request.environ
        start = time.time()
        ip_addr = self._get_ip_addr(environ)
        self._req_id = None
        if 'CONTENT_LENGTH' not in environ:
            log.debug("No Content-Length")
            raise JSONRPCErrorResponse(retid=self._req_id,
                                       message="No Content-Length in request")
        else:
            length = environ['CONTENT_LENGTH'] or 0
            length = int(environ['CONTENT_LENGTH'])
            log.debug('Content-Length: %s', length)

        if length == 0:
            raise JSONRPCErrorResponse(retid=self._req_id,
                                       message="Content-Length is 0")

        raw_body = environ['wsgi.input'].read(length)

        try:
            json_body = json.loads(raw_body)
        except ValueError as e:
            # catch JSON errors Here
            raise JSONRPCErrorResponse(retid=self._req_id,
                                       message="JSON parse error ERR:%s RAW:%r"
                                                % (e, raw_body))

        # check AUTH based on API key
        try:
            self._req_api_key = json_body['api_key']
            self._req_id = json_body['id']
            self._req_method = json_body['method']
            self._request_params = json_body['args']
            if not isinstance(self._request_params, dict):
                self._request_params = {}

            log.debug('method: %s, params: %s',
                      self._req_method, self._request_params)
        except KeyError as e:
            raise JSONRPCErrorResponse(retid=self._req_id,
                                       message='Incorrect JSON query missing %s' % e)

        # check if we can find this session using api_key
        try:
            u = User.get_by_api_key(self._req_api_key)
            auth_user = AuthUser.make(dbuser=u, ip_addr=ip_addr)
            if auth_user is None:
                raise JSONRPCErrorResponse(retid=self._req_id,
                                           message='Invalid API key')
        except Exception as e:
            raise JSONRPCErrorResponse(retid=self._req_id,
                                       message='Invalid API key')

        request.authuser = auth_user
        request.ip_addr = ip_addr

        self._error = None
        try:
            self._func = self._find_method()
        except AttributeError as e:
            raise JSONRPCErrorResponse(retid=self._req_id,
                                       message=str(e))

        # now that we have a method, add self._req_params to
        # self.kargs and dispatch control to WGIController
        argspec = inspect.getargspec(self._func)
        arglist = argspec[0][1:]
        defaults = map(type, argspec[3] or [])
        default_empty = types.NotImplementedType

        # kw arguments required by this method
        func_kwargs = dict(itertools.izip_longest(reversed(arglist), reversed(defaults),
                                                  fillvalue=default_empty))

        # This attribute will need to be first param of a method that uses
        # api_key, which is translated to instance of user at that name
        USER_SESSION_ATTR = 'apiuser'

        # get our arglist and check if we provided them as args
        for arg, default in func_kwargs.iteritems():
            if arg == USER_SESSION_ATTR:
                # USER_SESSION_ATTR is something translated from API key and
                # this is checked before so we don't need validate it
                continue

            # skip the required param check if it's default value is
            # NotImplementedType (default_empty)
            if default == default_empty and arg not in self._request_params:
                raise JSONRPCErrorResponse(
                    retid=self._req_id,
                    message='Missing non optional `%s` arg in JSON DATA' % arg,
                )

        extra = set(self._request_params).difference(func_kwargs)
        if extra:
            raise JSONRPCErrorResponse(
                retid=self._req_id,
                message='Unknown %s arg in JSON DATA' %
                        ', '.join('`%s`' % arg for arg in extra),
            )

        self._rpc_args = {}
        self._rpc_args.update(self._request_params)
        self._rpc_args['action'] = self._req_method
        self._rpc_args['environ'] = environ

        log.info('IP: %s Request to %s time: %.3fs' % (
            self._get_ip_addr(environ),
            safe_unicode(_get_access_path(environ)), time.time() - start)
        )

        state.set_action(self._rpc_call, [])
        state.set_params(self._rpc_args)
        return state

    def _rpc_call(self, action, environ, **rpc_args):
        """
        Call the specified RPC Method
        """
        raw_response = ''
        try:
            raw_response = getattr(self, action)(**rpc_args)
            if isinstance(raw_response, HTTPError):
                self._error = str(raw_response)
        except JSONRPCError as e:
            self._error = safe_str(e)
        except Exception as e:
            log.error('Encountered unhandled exception: %s',
                      traceback.format_exc(),)
            json_exc = JSONRPCError('Internal server error')
            self._error = safe_str(json_exc)

        if self._error is not None:
            raw_response = None

        response = dict(id=self._req_id, result=raw_response, error=self._error)
        try:
            return json.dumps(response)
        except TypeError as e:
            log.error('API FAILED. Error encoding response: %s', e)
            return json.dumps(
                dict(
                    id=self._req_id,
                    result=None,
                    error="Error encoding response"
                )
            )

    def _find_method(self):
        """
        Return method named by `self._req_method` in controller if able
        """
        log.debug('Trying to find JSON-RPC method: %s', self._req_method)
        if self._req_method.startswith('_'):
            raise AttributeError("Method not allowed")

        try:
            func = getattr(self, self._req_method, None)
        except UnicodeEncodeError:
            raise AttributeError("Problem decoding unicode in requested "
                                 "method name.")

        if isinstance(func, types.MethodType):
            return func
        else:
            raise AttributeError("No such method: %s" % (self._req_method,))
