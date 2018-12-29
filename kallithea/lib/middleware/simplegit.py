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
    HTTPNotAcceptable
from kallithea.model.db import Ui

from kallithea.lib.utils2 import safe_str, safe_unicode, fix_PATH, get_server_url, \
    _set_extras
from kallithea.lib.base import BaseVCSController, check_locking_state
from kallithea.lib.utils import make_ui, is_valid_repo
from kallithea.lib.exceptions import HTTPLockedRC
from kallithea.lib.hooks import pull_lock_handling

log = logging.getLogger(__name__)


GIT_PROTO_PAT = re.compile(r'^/(.+)/(info/refs|git-upload-pack|git-receive-pack)')


def is_git(environ):
    path_info = environ['PATH_INFO']
    isgit_path = GIT_PROTO_PAT.match(path_info)
    log.debug('pathinfo: %s detected as Git %s',
        path_info, isgit_path is not None
    )
    return isgit_path


class SimpleGit(BaseVCSController):

    _git_stored_op = 'pull' # most recent kind of command

    def _handle_request(self, environ, start_response):
        if not is_git(environ):
            return self.application(environ, start_response)

        ip_addr = self._get_ip_addr(environ)
        # skip passing error to error controller
        environ['pylons.status_code_redirect'] = True

        #======================================================================
        # EXTRACT REPOSITORY NAME FROM ENV
        #======================================================================
        try:
            str_repo_name = self.__get_repository(environ)
            repo_name = safe_unicode(str_repo_name)
            log.debug('Extracted repo name is %s', repo_name)
        except Exception as e:
            log.error('error extracting repo_name: %r', e)
            return HTTPInternalServerError()(environ, start_response)

        # quick check if that dir exists...
        if not is_valid_repo(repo_name, self.basepath, 'git'):
            return HTTPNotFound()(environ, start_response)

        #======================================================================
        # GET ACTION PULL or PUSH
        #======================================================================
        action = self.__get_action(environ)

        #======================================================================
        # CHECK PERMISSIONS
        #======================================================================
        user, response_app = self._authorize(environ, start_response, action, repo_name, ip_addr)
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
            'repository': repo_name,
            'scm': 'git',
            'config': CONFIG['__file__'],
            'server_url': server_url,
            'make_lock': None,
            'locked_by': [None, None]
        }

        #===================================================================
        # GIT REQUEST HANDLING
        #===================================================================
        repo_path = os.path.join(safe_str(self.basepath), str_repo_name)
        log.debug('Repository path is %s', repo_path)

        if not user.is_default_user:
            log.debug('Checking locking on repository')
            make_lock, locked, locked_by = check_locking_state(action, repo_name, user)
            # store the make_lock for later evaluation in hooks
            extras.update({'make_lock': make_lock,
                           'locked_by': locked_by})

        fix_PATH()
        log.debug('HOOKS extras is %s', extras)
        baseui = make_ui('db')
        _set_extras(extras or {})

        try:
            self._handle_githooks(repo_name, action, baseui, environ)
            log.info('%s action on Git repo "%s" by "%s" from %s',
                     action, str_repo_name, safe_str(user.username), ip_addr)
            app = self.__make_app(repo_name, repo_path, extras)
            return app(environ, start_response)
        except HTTPLockedRC as e:
            log.debug('Locked, response %s: %s', e.code, e.title)
            return e(environ, start_response)
        except Exception:
            log.error(traceback.format_exc())
            return HTTPInternalServerError()(environ, start_response)

    def __make_app(self, repo_name, repo_path, extras):
        """
        Make an wsgi application using dulserver

        :param repo_name: name of the repository
        :param repo_path: full path to the repository
        """

        from kallithea.lib.middleware.pygrack import make_wsgi_app
        app = make_wsgi_app(
            repo_root=safe_str(self.basepath),
            repo_name=safe_unicode(repo_name),
            extras=extras,
        )
        return app

    def __get_repository(self, environ):
        """
        Gets repository name out of PATH_INFO header

        :param environ: environ where PATH_INFO is stored
        """
        try:
            environ['PATH_INFO'] = self._get_by_id(environ['PATH_INFO'])
            repo_name = GIT_PROTO_PAT.match(environ['PATH_INFO']).group(1)
        except Exception:
            log.error(traceback.format_exc())
            raise

        return repo_name

    def __get_action(self, environ):
        """
        Maps Git request commands into a pull or push command.

        :param environ:
        """
        service = environ['QUERY_STRING'].split('=')

        if len(service) > 1:
            service_cmd = service[1]
            mapping = {
                'git-receive-pack': 'push',
                'git-upload-pack': 'pull',
            }
            op = mapping[service_cmd]
            self._git_stored_op = op
            # try to fallback to stored variable as we don't know if the last
            # operation is pull/push
        return self._git_stored_op

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

        _hooks = dict(baseui.configitems('hooks')) or {}
        if action == 'pull':
            # stupid git, emulate pre-pull hook !
            pull_lock_handling(ui=baseui, repo=_repo._repo)
        if action == 'pull' and _hooks.get(Ui.HOOK_PULL_LOG):
            log_pull_action(ui=baseui, repo=_repo._repo)
