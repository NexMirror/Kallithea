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
kallithea.lib.paster_commands.common
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Common code for gearbox commands.

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 18, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import os
import sys
import logging.config

import paste.deploy
import gearbox.command
from tg import config

import kallithea.config.middleware
import kallithea.model.base
import kallithea.lib.utils2
import kallithea.lib.utils


def ask_ok(prompt, retries=4, complaint='Yes or no please!'):
    while True:
        ok = raw_input(prompt)
        if ok in ('y', 'ye', 'yes'):
            return True
        if ok in ('n', 'no', 'nop', 'nope'):
            return False
        retries = retries - 1
        if retries < 0:
            raise IOError
        print complaint


class BasePasterCommand(gearbox.command.Command):
    """
    Abstract Base Class for gearbox commands.
    """

    # override to control how much get_parser and run should do:
    takes_config_file = True
    requires_db_session = True

    def run(self, args):
        """
        Overrides Command.run

        If needed by the command, read config file and initialize database before running.
        """
        if self.takes_config_file:
            path_to_ini_file = os.path.realpath(args.config_file)
            conf = paste.deploy.appconfig('config:' + path_to_ini_file)
            logging.config.fileConfig(path_to_ini_file)

            if self.requires_db_session:
                kallithea.config.middleware.make_app_without_logging(conf.global_conf, **conf.local_conf)
                kallithea.lib.utils.setup_cache_regions(config)
                engine = kallithea.lib.utils2.engine_from_config(config, 'sqlalchemy.')
                kallithea.model.base.init_model(engine)

        return super(BasePasterCommand, self).run(args)

    def get_parser(self, prog_name):
        parser = super(BasePasterCommand, self).get_parser(prog_name)

        if self.takes_config_file:
            parser.add_argument("-c", "--config",
                help='Kallithea .ini file with configuration of database etc',
                dest='config_file', required=True)

        return parser

    def error(self, msg, exitcode=1):
        """Write error message and exit"""
        sys.stderr.write('%s\n' % msg)
        raise SystemExit(exitcode)
