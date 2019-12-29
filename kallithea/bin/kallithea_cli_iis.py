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
import os
import sys

import click

import kallithea
import kallithea.bin.kallithea_cli_base as cli_base


dispath_py_template = '''\
# Created by Kallithea 'kallithea-cli iis-install'
import sys

if hasattr(sys, "isapidllhandle"):
    import win32traceutil

import isapi_wsgi
import os

def __ExtensionFactory__():
    from paste.deploy import loadapp
    from logging.config import fileConfig
    fileConfig('%(inifile)s', {'__file__': '%(inifile)s', 'here': '%(inifiledir)s'})

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

@cli_base.register_command(config_file=True)
@click.option('--virtualdir', default='/',
        help='The virtual folder to install into on IIS.')
def iis_install(virtualdir):
    """Install into IIS using isapi-wsgi."""

    config_file_abs = kallithea.CONFIG['__file__']

    try:
        import isapi_wsgi
    except ImportError:
        sys.stderr.write('missing requirement: isapi-wsgi not installed\n')
        sys.exit(1)

    dispatchfile = os.path.join(os.getcwd(), 'dispatch.py')
    click.echo('Writing %s' % dispatchfile)
    with open(dispatchfile, 'w') as f:
        f.write(dispath_py_template % {
            'inifile': config_file_abs.replace('\\', '\\\\'),
            'inifiledir': os.path.dirname(config_file_abs).replace('\\', '\\\\'),
            'virtualdir': virtualdir,
            })

    click.echo('Run \'python "%s" install\' with administrative privileges '
        'to generate the _dispatch.dll file and install it into the '
        'default web site' % dispatchfile)
