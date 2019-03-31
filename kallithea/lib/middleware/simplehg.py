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
kallithea.lib.middleware.simplehg
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SimpleHg middleware for handling Mercurial protocol requests (push/clone etc.).
It's implemented with basic auth function

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 28, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""


import os
import logging
import traceback
import urllib

from webob.exc import HTTPNotFound, HTTPForbidden, HTTPInternalServerError, \
    HTTPNotAcceptable, HTTPBadRequest

from kallithea.lib.utils2 import safe_str, safe_unicode, fix_PATH, get_server_url, \
    _set_extras
from kallithea.lib.base import BaseVCSController, check_locking_state
from kallithea.lib.utils import make_ui, is_valid_repo, ui_sections
from kallithea.lib.vcs.utils.hgcompat import RepoError, hgweb_mod
from kallithea.lib.exceptions import HTTPLockedRC

log = logging.getLogger(__name__)


def is_mercurial(environ):
    """
    Returns True if request's target is mercurial server - header
    ``HTTP_ACCEPT`` of such request would start with ``application/mercurial``.
    """
    http_accept = environ.get('HTTP_ACCEPT')
    path_info = environ['PATH_INFO']
    if http_accept and http_accept.startswith('application/mercurial'):
        ishg_path = True
    else:
        ishg_path = False

    log.debug('pathinfo: %s detected as Mercurial %s',
        path_info, ishg_path
    )
    return ishg_path


def get_header_hgarg(environ):
    """Decode the special Mercurial encoding of big requests over multiple headers.
    >>> get_header_hgarg({})
    ''
    >>> get_header_hgarg({'HTTP_X_HGARG_0': ' ', 'HTTP_X_HGARG_1': 'a','HTTP_X_HGARG_2': '','HTTP_X_HGARG_3': 'b+c %20'})
    'ab+c %20'
    """
    chunks = []
    i = 1
    while True:
        v = environ.get('HTTP_X_HGARG_%d' % i)
        if v is None:
            break
        chunks.append(v)
        i += 1
    return ''.join(chunks)


class SimpleHg(BaseVCSController):

    def _handle_request(self, environ, start_response):
        if not is_mercurial(environ):
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
        if not is_valid_repo(repo_name, self.basepath, 'hg'):
            return HTTPNotFound()(environ, start_response)

        #======================================================================
        # GET ACTION PULL or PUSH
        #======================================================================
        try:
            action = self.__get_action(environ)
        except HTTPBadRequest as e:
            return e(environ, start_response)

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
            'scm': 'hg',
            'config': CONFIG['__file__'],
            'server_url': server_url,
            'make_lock': None,
            'locked_by': [None, None]
        }
        #======================================================================
        # MERCURIAL REQUEST HANDLING
        #======================================================================
        repo_path = os.path.join(safe_str(self.basepath), str_repo_name)
        log.debug('Repository path is %s', repo_path)

        # A Mercurial HTTP server will see listkeys operations (bookmarks,
        # phases and obsolescence marker) in a different request - we don't
        # want to check locking on those
        if environ['QUERY_STRING'] == 'cmd=listkeys':
            pass
        # CHECK LOCKING only if it's not ANONYMOUS USER
        elif not user.is_default_user:
            log.debug('Checking locking on repository')
            make_lock, locked, locked_by = check_locking_state(action, repo_name, user)
            # store the make_lock for later evaluation in hooks
            extras.update({'make_lock': make_lock,
                           'locked_by': locked_by})

        fix_PATH()
        log.debug('HOOKS extras is %s', extras)
        baseui = make_ui('db')
        self._augment_hgrc(repo_path, baseui)
        _set_extras(extras or {})

        try:
            log.info('%s action on Mercurial repo "%s" by "%s" from %s',
                     action, str_repo_name, safe_str(user.username), ip_addr)
            environ['REPO_NAME'] = str_repo_name # used by hgweb_mod.hgweb
            app = self.__make_app(repo_path, baseui, extras)
            return app(environ, start_response)
        except RepoError as e:
            if str(e).find('not found') != -1:
                return HTTPNotFound()(environ, start_response)
        except HTTPLockedRC as e:
            # Before Mercurial 3.6, lock exceptions were caught here
            log.debug('Locked, response %s: %s', e.code, e.title)
            return e(environ, start_response)
        except Exception:
            log.error(traceback.format_exc())
            return HTTPInternalServerError()(environ, start_response)

    def __make_app(self, repo_name, baseui, extras):
        """
        Make an wsgi application using hgweb, and inject generated baseui
        instance, additionally inject some extras into ui object
        """
        class HgWebWrapper(hgweb_mod.hgweb):
            # Work-around for Mercurial 3.6+ causing lock exceptions to be
            # thrown late
            def _runwsgi(self, *args):
                try:
                    return super(HgWebWrapper, self)._runwsgi(*args)
                except HTTPLockedRC as e:
                    log.debug('Locked, response %s: %s', e.code, e.title)
                    try:
                        req, res, repo = args
                        res.status = e.status
                        res.headers['Content-Type'] = 'text/plain'
                        res.setbodybytes('')
                        return res.sendresponse()
                    except ValueError: # wsgiresponse was introduced in Mercurial 4.6 (a88d68dc3ee8)
                        req, repo = args
                        req.respond(e.status, 'text/plain')
                        return ''

        return HgWebWrapper(repo_name, name=repo_name, baseui=baseui)

    def __get_repository(self, environ):
        """
        Gets repository name out of PATH_INFO header

        :param environ: environ where PATH_INFO is stored
        """
        try:
            environ['PATH_INFO'] = self._get_by_id(environ['PATH_INFO'])
            repo_name = '/'.join(environ['PATH_INFO'].split('/')[1:])
            if repo_name.endswith('/'):
                repo_name = repo_name.rstrip('/')
        except Exception:
            log.error(traceback.format_exc())
            raise

        return repo_name

    def __get_action(self, environ):
        """
        Maps Mercurial request commands into 'pull' or 'push'.

        Raises HTTPBadRequest if the request environment doesn't look like a hg client.
        """
        mapping = {
            # 'batch' is not in this list - it is handled explicitly
            'between': 'pull',
            'branches': 'pull',
            'branchmap': 'pull',
            'capabilities': 'pull',
            'changegroup': 'pull',
            'changegroupsubset': 'pull',
            'changesetdata': 'pull',
            'clonebundles': 'pull',
            'debugwireargs': 'pull',
            'filedata': 'pull',
            'getbundle': 'pull',
            'getlfile': 'pull',
            'heads': 'pull',
            'hello': 'pull',
            'known': 'pull',
            'lheads': 'pull',
            'listkeys': 'pull',
            'lookup': 'pull',
            'manifestdata': 'pull',
            'narrow_widen': 'pull',
            'protocaps': 'pull',
            'statlfile': 'pull',
            'stream_out': 'pull',
            'pushkey': 'push',
            'putlfile': 'push',
            'unbundle': 'push',
            }
        for qry in environ['QUERY_STRING'].split('&'):
            parts = qry.split('=', 1)
            if len(parts) == 2 and parts[0] == 'cmd':
                cmd = parts[1]
                if cmd == 'batch':
                    hgarg = get_header_hgarg(environ)
                    if not hgarg.startswith('cmds='):
                        return 'push' # paranoid and safe
                    for cmd_arg in hgarg[5:].split(';'):
                        cmd, _args = urllib.unquote_plus(cmd_arg).split(' ', 1)
                        op = mapping.get(cmd, 'push')
                        if op != 'pull':
                            assert op == 'push'
                            return 'push'
                    return 'pull'
                return mapping.get(cmd, 'push')

        # Note: the client doesn't get the helpful error message
        raise HTTPBadRequest('Unable to detect pull/push action! Are you using non standard command or client?')

    def _augment_hgrc(self, repo_path, baseui):
        """Augment baseui with config settings from the repo_path repo"""
        hgrc = os.path.join(repo_path, '.hg', 'hgrc')
        repoui = make_ui('file', hgrc)
        for section in ui_sections:
            for k, v in repoui.configitems(section):
                baseui.setconfig(section, k, v)
