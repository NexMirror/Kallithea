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

from __future__ import with_statement

import os
import sys
import logging
import pkg_resources

from kallithea.lib.utils import BasePasterCommand, ask_ok

# Add location of top level folder to sys.path
from os.path import dirname as dn
rc_path = dn(dn(dn(os.path.realpath(__file__))))
sys.path.append(rc_path)

log = logging.getLogger(__name__)


class Command(BasePasterCommand):

    max_args = 1
    min_args = 1

    usage = "CONFIG_FILE"
    group_name = "Kallithea"
    takes_config_file = -1
    parser = BasePasterCommand.standard_parser(verbose=True)
    summary = "Creates additional extensions for kallithea"

    def command(self):
        logging.config.fileConfig(self.path_to_ini_file)
        from pylons import config

        def _make_file(ext_file, tmpl):
            bdir = os.path.split(ext_file)[0]
            if not os.path.isdir(bdir):
                os.makedirs(bdir)
            with open(ext_file, 'wb') as f:
                f.write(tmpl)
                log.info('Writen new extensions file to %s' % ext_file)

        here = config['here']
        tmpl = pkg_resources.resource_string(
            'kallithea', os.path.join('config', 'rcextensions', '__init__.py')
        )
        ext_file = os.path.join(here, 'rcextensions', '__init__.py')
        if os.path.exists(ext_file):
            msg = ('Extension file already exists, do you want '
                   'to overwrite it ? [y/n]')
            if ask_ok(msg):
                _make_file(ext_file, tmpl)
            else:
                log.info('nothing done...')
        else:
            _make_file(ext_file, tmpl)

    def update_parser(self):
        pass
