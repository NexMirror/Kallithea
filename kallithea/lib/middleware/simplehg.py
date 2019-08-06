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


import logging
import os
import urllib

from kallithea.lib.base import BaseVCSController
from kallithea.lib.utils import make_ui
from kallithea.lib.utils2 import safe_str, safe_unicode
from kallithea.lib.vcs.utils.hgcompat import hgweb_mod


log = logging.getLogger(__name__)


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


cmd_mapping = {
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


class SimpleHg(BaseVCSController):

    scm_alias = 'hg'

    @classmethod
    def parse_request(cls, environ):
        http_accept = environ.get('HTTP_ACCEPT', '')
        if not http_accept.startswith('application/mercurial'):
            return None
        path_info = environ.get('PATH_INFO', '')
        if not path_info.startswith('/'): # it must!
            return None

        class parsed_request(object):
            repo_name = safe_unicode(path_info[1:].rstrip('/'))

            query_string = environ['QUERY_STRING']

            action = None
            for qry in query_string.split('&'):
                parts = qry.split('=', 1)
                if len(parts) == 2 and parts[0] == 'cmd':
                    cmd = parts[1]
                    if cmd == 'batch':
                        hgarg = get_header_hgarg(environ)
                        if not hgarg.startswith('cmds='):
                            action = 'push' # paranoid and safe
                            break
                        action = 'pull'
                        for cmd_arg in hgarg[5:].split(';'):
                            cmd, _args = urllib.unquote_plus(cmd_arg).split(' ', 1)
                            op = cmd_mapping.get(cmd, 'push')
                            if op != 'pull':
                                assert op == 'push'
                                action = 'push'
                                break
                    else:
                        action = cmd_mapping.get(cmd, 'push')
                    break # only process one cmd

        return parsed_request

    def _make_app(self, parsed_request):
        """
        Make an hgweb wsgi application.
        """
        str_repo_name = safe_str(parsed_request.repo_name)
        repo_path = os.path.join(safe_str(self.basepath), str_repo_name)
        baseui = make_ui(repo_path=repo_path)
        hgweb_app = hgweb_mod.hgweb(repo_path, name=str_repo_name, baseui=baseui)

        def wrapper_app(environ, start_response):
            environ['REPO_NAME'] = str_repo_name # used by hgweb_mod.hgweb
            return hgweb_app(environ, start_response)

        return wrapper_app
