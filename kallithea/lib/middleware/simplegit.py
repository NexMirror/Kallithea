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
kallithea.lib.middleware.simplegit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SimpleGit middleware for handling Git protocol requests (push/clone etc.)
It's implemented with basic auth function

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 28, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""


import os
import re
import logging
import traceback

from webob.exc import HTTPNotFound, HTTPForbidden, HTTPInternalServerError, \
    HTTPNotAcceptable, HTTPBadRequest
from kallithea.model.db import Ui

from kallithea.lib.utils2 import safe_str, safe_unicode, get_server_url, \
    _set_extras
from kallithea.lib.base import BaseVCSController
from kallithea.lib.utils import make_ui, is_valid_repo
from kallithea.lib.middleware.pygrack import make_wsgi_app

log = logging.getLogger(__name__)


GIT_PROTO_PAT = re.compile(r'^/(.+)/(info/refs|git-upload-pack|git-receive-pack)$')


class SimpleGit(BaseVCSController):

    @classmethod
    def parse_request(cls, environ):
        path_info = environ.get('PATH_INFO', '')
        m = GIT_PROTO_PAT.match(path_info)
        if m is None:
            return None

        class parsed_request(object):
            repo_name = safe_unicode(m.group(1).rstrip('/'))
            cmd = m.group(2)

        return parsed_request

    def _handle_request(self, parsed_request, environ, start_response):
        ip_addr = self._get_ip_addr(environ)
        # skip passing error to error controller
        environ['pylons.status_code_redirect'] = True

        # quick check if repo exists...
        if not is_valid_repo(parsed_request.repo_name, self.basepath, 'git'):
            raise HTTPNotFound()

        #======================================================================
        # GET ACTION PULL or PUSH
        #======================================================================
        action = self.__get_action(environ)

        #======================================================================
        # CHECK PERMISSIONS
        #======================================================================
        user, response_app = self._authorize(environ, start_response, action, parsed_request.repo_name, ip_addr)
        if response_app is not None:
            return response_app(environ, start_response)

        # extras are injected into Mercurial UI object and later available
        # in hooks executed by Kallithea
        from kallithea import CONFIG
        server_url = get_server_url(environ)
        extras = {
            'ip': ip_addr,
            'username': user.username,
            'action': action,
            'repository': parsed_request.repo_name,
            'scm': 'git',
            'config': CONFIG['__file__'],
            'server_url': server_url,
        }

        #===================================================================
        # GIT REQUEST HANDLING
        #===================================================================
        log.debug('HOOKS extras is %s', extras)
        baseui = make_ui()
        _set_extras(extras or {})

        try:
            self._handle_githooks(parsed_request.repo_name, action, baseui, environ)
            log.info('%s action on Git repo "%s" by "%s" from %s',
                     action, parsed_request.repo_name, safe_str(user.username), ip_addr)
            app = self.__make_app(parsed_request.repo_name)
            return app(environ, start_response)
        except Exception:
            log.error(traceback.format_exc())
            raise HTTPInternalServerError()

    def __make_app(self, repo_name):
        """
        Return a pygrack wsgi application.
        """
        return make_wsgi_app(repo_name, safe_str(self.basepath)) # FIXME: safe_str???

    def __get_action(self, environ):
        """
        Maps Git request commands into 'pull' or 'push'.

        Raises HTTPBadRequest if the request environment doesn't look like a git client.
        """
        mapping = {
            'git-receive-pack': 'push',
            'git-upload-pack': 'pull',
        }
        path_info = environ.get('PATH_INFO', '')
        m = GIT_PROTO_PAT.match(path_info)
        if m is None:
            action = None
        else:
            cmd = m.group(2)
            query_string = environ['QUERY_STRING']
            if cmd == 'info/refs' and query_string.startswith('service='):
                service = query_string.split('=', 1)[1]
                action = mapping.get(service)
            else:
                action = mapping.get(cmd)
        if action is None:
            raise HTTPBadRequest('Unable to detect pull/push action for %r! Are you using a nonstandard command or client?' % path_info)
        return action

    def _handle_githooks(self, repo_name, action, baseui, environ):
        """
        Handles pull action, push is handled by post-receive hook
        """
        from kallithea.lib.hooks import log_pull_action
        service = environ['QUERY_STRING'].split('=')

        if len(service) < 2:
            return

        from kallithea.model.db import Repository
        _repo = Repository.get_by_repo_name(repo_name)
        _repo = _repo.scm_instance

        if action == 'pull':
            log_pull_action(ui=baseui, repo=_repo._repo)
