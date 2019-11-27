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
kallithea.lib.middleware.pygrack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python implementation of git-http-backend's Smart HTTP protocol

Based on original code from git_http_backend.py project.

Copyright (c) 2010 Daniel Dotsenko <dotsa@hotmail.com>
Copyright (c) 2012 Marcin Kuzminski <marcin@python-works.com>

This file was forked by the Kallithea project in July 2014.
"""

import logging
import os
import socket
import traceback

from webob import Request, Response, exc

import kallithea
from kallithea.lib.utils2 import safe_unicode
from kallithea.lib.vcs import subprocessio


log = logging.getLogger(__name__)


class FileWrapper(object):

    def __init__(self, fd, content_length):
        self.fd = fd
        self.content_length = content_length
        self.remain = content_length

    def read(self, size):
        if size <= self.remain:
            try:
                data = self.fd.read(size)
            except socket.error:
                raise IOError(self)
            self.remain -= size
        elif self.remain:
            data = self.fd.read(self.remain)
            self.remain = 0
        else:
            data = None
        return data

    def __repr__(self):
        return '<FileWrapper %s len: %s, read: %s>' % (
            self.fd, self.content_length, self.content_length - self.remain
        )


class GitRepository(object):
    git_folder_signature = set(['config', 'head', 'info', 'objects', 'refs'])
    commands = ['git-upload-pack', 'git-receive-pack']

    def __init__(self, repo_name, content_path):
        files = set([f.lower() for f in os.listdir(content_path)])
        if not (self.git_folder_signature.intersection(files)
                == self.git_folder_signature):
            raise OSError('%s missing git signature' % content_path)
        self.content_path = content_path
        self.valid_accepts = ['application/x-%s-result' %
                              c for c in self.commands]
        self.repo_name = repo_name

    def _get_fixedpath(self, path):
        """
        Small fix for repo_path

        :param path:
        """
        path = safe_unicode(path)
        assert path.startswith('/' + self.repo_name + '/')
        return path[len(self.repo_name) + 2:].strip('/')

    def inforefs(self, req, environ):
        """
        WSGI Response producer for HTTP GET Git Smart
        HTTP /info/refs request.
        """

        git_command = req.GET.get('service')
        if git_command not in self.commands:
            log.debug('command %s not allowed', git_command)
            return exc.HTTPMethodNotAllowed()

        # From Documentation/technical/http-protocol.txt shipped with Git:
        #
        # Clients MUST verify the first pkt-line is `# service=$servicename`.
        # Servers MUST set $servicename to be the request parameter value.
        # Servers SHOULD include an LF at the end of this line.
        # Clients MUST ignore an LF at the end of the line.
        #
        #  smart_reply     =  PKT-LINE("# service=$servicename" LF)
        #                     ref_list
        #                     "0000"
        server_advert = '# service=%s\n' % git_command
        packet_len = str(hex(len(server_advert) + 4)[2:].rjust(4, '0')).lower()
        _git_path = kallithea.CONFIG.get('git_path', 'git')
        cmd = [_git_path, git_command[4:],
               '--stateless-rpc', '--advertise-refs', self.content_path]
        log.debug('handling cmd %s', cmd)
        try:
            out = subprocessio.SubprocessIOChunker(cmd,
                starting_values=[packet_len + server_advert + '0000']
            )
        except EnvironmentError as e:
            log.error(traceback.format_exc())
            raise exc.HTTPExpectationFailed()
        resp = Response()
        resp.content_type = 'application/x-%s-advertisement' % str(git_command)
        resp.charset = None
        resp.app_iter = out
        return resp

    def backend(self, req, environ):
        """
        WSGI Response producer for HTTP POST Git Smart HTTP requests.
        Reads commands and data from HTTP POST's body.
        returns an iterator obj with contents of git command's
        response to stdout
        """
        _git_path = kallithea.CONFIG.get('git_path', 'git')
        git_command = self._get_fixedpath(req.path_info)
        if git_command not in self.commands:
            log.debug('command %s not allowed', git_command)
            return exc.HTTPMethodNotAllowed()

        if 'CONTENT_LENGTH' in environ:
            inputstream = FileWrapper(environ['wsgi.input'],
                                      req.content_length)
        else:
            inputstream = environ['wsgi.input']

        gitenv = dict(os.environ)
        # forget all configs
        gitenv['GIT_CONFIG_NOGLOBAL'] = '1'
        cmd = [_git_path, git_command[4:], '--stateless-rpc', self.content_path]
        log.debug('handling cmd %s', cmd)
        try:
            out = subprocessio.SubprocessIOChunker(
                cmd,
                inputstream=inputstream,
                env=gitenv,
                cwd=self.content_path,
            )
        except EnvironmentError as e:
            log.error(traceback.format_exc())
            raise exc.HTTPExpectationFailed()

        if git_command in [u'git-receive-pack']:
            # updating refs manually after each push.
            # Needed for pre-1.7.0.4 git clients using regular HTTP mode.
            from kallithea.lib.vcs import get_repo
            from dulwich.server import update_server_info
            repo = get_repo(self.content_path)
            if repo:
                update_server_info(repo._repo)

        resp = Response()
        resp.content_type = 'application/x-%s-result' % git_command.encode('utf-8')
        resp.charset = None
        resp.app_iter = out
        return resp

    def __call__(self, environ, start_response):
        req = Request(environ)
        _path = self._get_fixedpath(req.path_info)
        if _path.startswith('info/refs'):
            app = self.inforefs
        elif [a for a in self.valid_accepts if a in req.accept]:
            app = self.backend
        try:
            resp = app(req, environ)
        except exc.HTTPException as e:
            resp = e
            log.error(traceback.format_exc())
        except Exception as e:
            log.error(traceback.format_exc())
            resp = exc.HTTPInternalServerError()
        return resp(environ, start_response)


class GitDirectory(object):

    def __init__(self, repo_root, repo_name):
        repo_location = os.path.join(repo_root, repo_name)
        if not os.path.isdir(repo_location):
            raise OSError(repo_location)

        self.content_path = repo_location
        self.repo_name = repo_name
        self.repo_location = repo_location

    def __call__(self, environ, start_response):
        content_path = self.content_path
        try:
            app = GitRepository(self.repo_name, content_path)
        except (AssertionError, OSError):
            content_path = os.path.join(content_path, '.git')
            if os.path.isdir(content_path):
                app = GitRepository(self.repo_name, content_path)
            else:
                return exc.HTTPNotFound()(environ, start_response)
        return app(environ, start_response)


def make_wsgi_app(repo_name, repo_root):
    from dulwich.web import LimitedInputFilter, GunzipFilter
    app = GitDirectory(repo_root, repo_name)
    return GunzipFilter(LimitedInputFilter(app))
