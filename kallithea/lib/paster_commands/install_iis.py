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
from paste.script.appinstall import AbstractInstallCommand
from paste.script.command import BadCommand

# Add location of top level folder to sys.path
from os.path import dirname as dn
rc_path = dn(dn(dn(os.path.realpath(__file__))))
sys.path.append(rc_path)

class Command(AbstractInstallCommand):
    default_verbosity = 1
    max_args = 1
    min_args = 1
    summary = 'Setup IIS given a config file'
    usage = 'CONFIG_FILE'

    description = '''
    Script for installing into IIS using isapi-wsgi.
    '''
    parser = AbstractInstallCommand.standard_parser(
        simulate=True, quiet=True, interactive=True)
    parser.add_option('--virtualdir',
                      action='store',
                      dest='virtualdir',
                      default='/',
                      help='The virtual folder to install into on IIS')

    def command(self):
        config_spec = self.args[0]
        if not config_spec.startswith('config:'):
            config_spec = 'config:' + config_spec
        config_file = config_spec[len('config:'):].split('#', 1)[0]
        config_file = os.path.join(os.getcwd(), config_file)
        try:
            import isapi_wsgi
        except ImportError:
            raise BadCommand('missing requirement: isapi-wsgi not installed')

        file = '''\
# Created by Kallithea install_iis
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

        outdata = file % {
                'inifile': config_file.replace('\\', '\\\\'),
                'virtualdir': self.options.virtualdir
                }

        dispatchfile = os.path.join(os.getcwd(), 'dispatch.py')
        self.ensure_file(dispatchfile, outdata, False)
        print 'Generating %s' % (dispatchfile,)

        print ('Run \'python "%s" install\' with administrative privileges '
            'to generate the _dispatch.dll file and install it into the '
            'default web site') % (dispatchfile,)
