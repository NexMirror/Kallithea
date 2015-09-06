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
kallithea.lib.paster_commands.make_rcextensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

make-rcext paster command for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Mar 6, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""


import os
import sys
import pkg_resources

from kallithea.lib.utils import BasePasterCommand, ask_ok

# Add location of top level folder to sys.path
from os.path import dirname as dn
rc_path = dn(dn(dn(os.path.realpath(__file__))))
sys.path.append(rc_path)


class Command(BasePasterCommand):

    max_args = 1
    min_args = 1

    group_name = "Kallithea"
    takes_config_file = -1
    parser = BasePasterCommand.standard_parser(verbose=True)
    summary = "Write template file for extending Kallithea in Python."
    usage = "CONFIG_FILE"
    description = '''\
        A rcextensions directory with a __init__.py file will be created next to
        the ini file. Local customizations in that file will survive upgrades.
        The file contains instructions on how it can be customized.
        '''

    def command(self):
        from pylons import config

        here = config['here']
        content = pkg_resources.resource_string(
            'kallithea', os.path.join('config', 'rcextensions', '__init__.py')
        )
        ext_file = os.path.join(here, 'rcextensions', '__init__.py')
        if os.path.exists(ext_file):
            msg = ('Extension file already exists, do you want '
                   'to overwrite it ? [y/n]')
            if not ask_ok(msg):
                print 'Nothing done...'
                return

        dirname = os.path.dirname(ext_file)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        with open(ext_file, 'wb') as f:
            f.write(content)
            print 'Wrote new extensions file to %s' % ext_file

    def update_parser(self):
        pass
