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
kallithea.lib.paster_commands.make_config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

make-config gearbox command for Kallithea

:license: GPLv3, see LICENSE.md for more details.
"""


import os
import sys
import uuid
import argparse
from collections import defaultdict

import mako.exceptions

from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.lib import inifile


class Command(BasePasterCommand):
    """Kallithea: Create a new config file

    make-config is part of a two-phase installation process (the
    second phase is setup-app). make-config creates a bare configuration
    file (possibly filling in defaults from the extra
    variables you give).

    The first key=value arguments are used to customize the Mako variables from
    what is shown with --show-defaults. Any following key=value arguments will be
    patched/inserted in the [app:main] section ... until another section name
    is specified and change where the following values go.
    """

    takes_config_file = False # at least not an existing one ...

    def take_action(self, args):
        _run(args)

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument('config_file', nargs='?',
            help='application config file to write')

        parser.add_argument('custom', nargs=argparse.REMAINDER,
            help='"key=value" for customizing the config file')

        parser.add_argument('--show-defaults', action='store_true',
            help="Show the default values that can be overridden")

        return parser


def _run(args):
    if args.show_defaults:
        if args.config_file is not None:
            raise ValueError("Can't specify both config file and --show-defaults")
        for key, value in inifile.default_variables.items():
            print '%s=%s' % (key, value)
        sys.exit(0)
    if args.config_file is None:
        raise ValueError("Missing argument: config file")

    mako_variable_values = {}
    ini_settings = defaultdict(dict)

    section_name = None
    for parameter in args.custom:
        parts = parameter.split('=', 1)
        if len(parts) == 1 and parameter.startswith('[') and parameter.endswith(']'):
            section_name = parameter
        elif len(parts) == 2:
            key, value = parts
            if section_name is None and key in inifile.default_variables:
                mako_variable_values[key] = value
            else:
                if section_name is None:
                    section_name = '[app:main]'
                ini_settings[section_name][key] = value
        else:
            raise ValueError("Invalid name=value parameter %r" % parameter)

    # use default that cannot be replaced
    mako_variable_values.update({
        'uuid': lambda: uuid.uuid4().hex,
    })
    try:
        config_file = os.path.abspath(args.config_file)
        inifile.create(config_file, mako_variable_values, ini_settings)
        print 'Wrote new config file in %s' % config_file

    except Exception:
        print mako.exceptions.text_error_template().render()
