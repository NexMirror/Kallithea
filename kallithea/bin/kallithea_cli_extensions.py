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
This file was forked by the Kallithea project in July 2014 and later moved.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Mar 6, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""
import os

import click
import pkg_resources

import kallithea
import kallithea.bin.kallithea_cli_base as cli_base
from kallithea.lib.utils2 import ask_ok


@cli_base.register_command(config_file=True)
def extensions_create():
    """Write template file for extending Kallithea in Python.

    An rcextensions directory with a __init__.py file will be created next to
    the ini file. Local customizations in that file will survive upgrades.
    The file contains instructions on how it can be customized.
    """
    here = kallithea.CONFIG['here']
    content = pkg_resources.resource_string(
        'kallithea', os.path.join('config', 'rcextensions', '__init__.py')
    )
    ext_file = os.path.join(here, 'rcextensions', '__init__.py')
    if os.path.exists(ext_file):
        msg = ('Extension file %s already exists, do you want '
               'to overwrite it ? [y/n] ') % ext_file
        if not ask_ok(msg):
            click.echo('Nothing done, exiting...')
            return

    dirname = os.path.dirname(ext_file)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(ext_file, 'wb') as f:
        f.write(content)
        click.echo('Wrote new extensions file to %s' % ext_file)
