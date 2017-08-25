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
kallithea.lib.paster_commands.install_iis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

IIS installation tools for Kallithea
"""


import os
import sys

from kallithea.lib.paster_commands.common import BasePasterCommand


dispath_py_template = '''\
# Created by Kallithea 'gearbox install-iis'
import sys

if hasattr(sys, "isapidllhandle"):
    import win32traceutil

import isapi_wsgi
import os

def __ExtensionFactory__():
    from paste.deploy import loadapp
    from paste.script.util.logging_config import fileConfig
    fileConfig('%(inifile)s')
    application = loadapp('config:%(inifile)s')

    def app(environ, start_response):
        user = environ.get('REMOTE_USER', None)
        if user is not None:
            os.environ['REMOTE_USER'] = user
        return application(environ, start_response)

    return isapi_wsgi.ISAPIThreadPoolHandler(app)

if __name__=='__main__':
    from isapi.install import *
    params = ISAPIParameters()
    sm = [ScriptMapParams(Extension="*", Flags=0)]
    vd = VirtualDirParameters(Name="%(virtualdir)s",
                              Description = "Kallithea",
                              ScriptMaps = sm,
                              ScriptMapUpdate = "replace")
    params.VirtualDirs = [vd]
    HandleCommandLine(params)
'''


class Command(BasePasterCommand):
    '''Kallithea: Install into IIS using isapi-wsgi'''

    requires_db_session = False

    def take_action(self, args):
        config_file = os.path.abspath(args.config_file)
        try:
            import isapi_wsgi
        except ImportError:
            self.error('missing requirement: isapi-wsgi not installed')

        dispatchfile = os.path.join(os.getcwd(), 'dispatch.py')
        print 'Writing %s' % dispatchfile
        with open(dispatchfile, 'w') as f:
            f.write(dispath_py_template % {
                'inifile': config_file.replace('\\', '\\\\'),
                'virtualdir': args.virtualdir,
                })

        print ('Run \'python "%s" install\' with administrative privileges '
            'to generate the _dispatch.dll file and install it into the '
            'default web site') % (dispatchfile,)

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument('--virtualdir',
                      action='store',
                      dest='virtualdir',
                      default='/',
                      help='The virtual folder to install into on IIS')

        return parser
