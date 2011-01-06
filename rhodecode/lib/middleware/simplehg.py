#!/usr/bin/env python
# encoding: utf-8
# middleware to handle mercurial api calls
# Copyright (C) 2009-2010 Marcin Kuzminski <marcin@python-works.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your opinion) any later version of the license.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.
"""
Created on 2010-04-28

@author: marcink
SimpleHG middleware for handling mercurial protocol request (push/clone etc.)
It's implemented with basic auth function
"""
from mercurial.error import RepoError
from mercurial.hgweb import hgweb
from mercurial.hgweb.request import wsgiapplication
from paste.auth.basic import AuthBasicAuthenticator
from paste.httpheaders import REMOTE_USER, AUTH_TYPE
from rhodecode.lib.auth import authfunc, HasPermissionAnyMiddleware
from rhodecode.lib.utils import make_ui, invalidate_cache, \
    check_repo_fast, ui_sections
from rhodecode.model.user import UserModel
from webob.exc import HTTPNotFound, HTTPForbidden, HTTPInternalServerError
import logging
import os
import traceback

log = logging.getLogger(__name__)

def is_mercurial(environ):
    """
    Returns True if request's target is mercurial server - header
    ``HTTP_ACCEPT`` of such request would start with ``application/mercurial``.
    """
    http_accept = environ.get('HTTP_ACCEPT')
    if http_accept and http_accept.startswith('application/mercurial'):
        return True
    return False

class SimpleHg(object):

    def __init__(self, application, config):
        self.application = application
        self.config = config
        #authenticate this mercurial request using authfunc
        self.authenticate = AuthBasicAuthenticator('', authfunc)
        self.ipaddr = '0.0.0.0'
        self.repository = None
        self.username = None
        self.action = None

    def __call__(self, environ, start_response):
        if not is_mercurial(environ):
            return self.application(environ, start_response)

        proxy_key = 'HTTP_X_REAL_IP'
        def_key = 'REMOTE_ADDR'
        self.ipaddr = environ.get(proxy_key, environ.get(def_key, '0.0.0.0'))
        # skip passing error to error controller
        environ['pylons.status_code_redirect'] = True

        #===================================================================
        # AUTHENTICATE THIS MERCURIAL REQUEST
        #===================================================================
        username = REMOTE_USER(environ)

        if not username:
            self.authenticate.realm = str(self.config['rhodecode_realm'])
            result = self.authenticate(environ)
            if isinstance(result, str):
                AUTH_TYPE.update(environ, 'basic')
                REMOTE_USER.update(environ, result)
            else:
                return result.wsgi_application(environ, start_response)

        #=======================================================================
        # GET REPOSITORY
        #=======================================================================
        try:
            repo_name = '/'.join(environ['PATH_INFO'].split('/')[1:])
            if repo_name.endswith('/'):
                repo_name = repo_name.rstrip('/')
            self.repository = repo_name
        except:
            log.error(traceback.format_exc())
            return HTTPInternalServerError()(environ, start_response)

        #===================================================================
        # CHECK PERMISSIONS FOR THIS REQUEST
        #===================================================================
        self.action = self.__get_action(environ)
        if self.action:
            username = self.__get_environ_user(environ)
            try:
                user = self.__get_user(username)
                self.username = user.username
            except:
                log.error(traceback.format_exc())
                return HTTPInternalServerError()(environ, start_response)

            #check permissions for this repository
            if self.action == 'push':
                if not HasPermissionAnyMiddleware('repository.write',
                                                  'repository.admin')\
                                                    (user, repo_name):
                    return HTTPForbidden()(environ, start_response)

            else:
                #any other action need at least read permission
                if not HasPermissionAnyMiddleware('repository.read',
                                                  'repository.write',
                                                  'repository.admin')\
                                                    (user, repo_name):
                    return HTTPForbidden()(environ, start_response)

        self.extras = {'ip':self.ipaddr,
                       'username':self.username,
                       'action':self.action,
                       'repository':self.repository}

        #===================================================================
        # MERCURIAL REQUEST HANDLING
        #===================================================================
        environ['PATH_INFO'] = '/'#since we wrap into hgweb, reset the path
        self.baseui = make_ui('db')
        self.basepath = self.config['base_path']
        self.repo_path = os.path.join(self.basepath, repo_name)

        #quick check if that dir exists...
        if check_repo_fast(repo_name, self.basepath):
            return HTTPNotFound()(environ, start_response)
        try:
            app = wsgiapplication(self.__make_app)
        except RepoError, e:
            if str(e).find('not found') != -1:
                return HTTPNotFound()(environ, start_response)
        except Exception:
            log.error(traceback.format_exc())
            return HTTPInternalServerError()(environ, start_response)

        #invalidate cache on push
        if self.action == 'push':
            self.__invalidate_cache(repo_name)

        return app(environ, start_response)


    def __make_app(self):
        hgserve = hgweb(str(self.repo_path), baseui=self.baseui)
        return  self.__load_web_settings(hgserve, self.extras)

    def __get_environ_user(self, environ):
        return environ.get('REMOTE_USER')

    def __get_user(self, username):
        return UserModel().get_by_username(username, cache=True)

    def __get_action(self, environ):
        """
        Maps mercurial request commands into a clone,pull or push command.
        This should always return a valid command string
        :param environ:
        """
        mapping = {'changegroup': 'pull',
                   'changegroupsubset': 'pull',
                   'stream_out': 'pull',
                   'listkeys': 'pull',
                   'unbundle': 'push',
                   'pushkey': 'push', }
        for qry in environ['QUERY_STRING'].split('&'):
            if qry.startswith('cmd'):
                cmd = qry.split('=')[-1]
                if mapping.has_key(cmd):
                    return mapping[cmd]
                else:
                    return cmd

    def __invalidate_cache(self, repo_name):
        """we know that some change was made to repositories and we should
        invalidate the cache to see the changes right away but only for
        push requests"""
        invalidate_cache('get_repo_cached_%s' % repo_name)


    def __load_web_settings(self, hgserve, extras={}):
        #set the global ui for hgserve instance passed
        hgserve.repo.ui = self.baseui

        hgrc = os.path.join(self.repo_path, '.hg', 'hgrc')

        #inject some additional parameters that will be available in ui
        #for hooks
        for k, v in extras.items():
            hgserve.repo.ui.setconfig('rhodecode_extras', k, v)

        repoui = make_ui('file', hgrc, False)

        if repoui:
            #overwrite our ui instance with the section from hgrc file
            for section in ui_sections:
                for k, v in repoui.configitems(section):
                    hgserve.repo.ui.setconfig(section, k, v)

        return hgserve














