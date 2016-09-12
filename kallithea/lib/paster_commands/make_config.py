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
from mako.template import Template
TMPL = 'template.ini.mako'
here = os.path.dirname(os.path.abspath(__file__))

from kallithea.lib.paster_commands.common import ask_ok, BasePasterCommand


class Command(BasePasterCommand):
    """Kallithea: Create a new config file

    make-config is part of a two-phase installation process (the
    second phase is setup-app). make-config creates a bare configuration
    file (possibly filling in defaults from the extra
    variables you give).
    """

    takes_config_file = False # at least not an existing one ...

    def take_action(self, args):
        _run(args)

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument('config_file', nargs='?',
            help='application config file to write')

        parser.add_argument('custom', nargs=argparse.REMAINDER,
            help='custom values to write to config file')

        parser.add_argument('--show-defaults', action='store_true',
            help="Show the default values that can be overridden")

        return parser


def _escape_split(text, sep):
    """
    Allows for escaping of the separator: e.g. arg='foo\, bar'

    It should be noted that the way bash et. al. do command line parsing, those
    single quotes are required. a shameless ripoff from fabric project.

    """
    escaped_sep = r'\%s' % sep

    if escaped_sep not in text:
        return text.split(sep)

    before, _, after = text.partition(escaped_sep)
    startlist = before.split(sep)  # a regular split is fine here
    unfinished = startlist[-1]
    startlist = startlist[:-1]

    # recurse because there may be more escaped separators
    endlist = _escape_split(after, sep)

    # finish building the escaped value. we use endlist[0] because the first
    # part of the string sent in recursion is the rest of the escaped value.
    unfinished += sep + endlist[0]

    return startlist + [unfinished] + endlist[1:]  # put together all the parts


def _run(args):
    if args.config_file is None:
        if not args.show_defaults:
            raise ValueError("Missing argument: config_file")
    else:
        if args.show_defaults:
            raise ValueError("Can't specify both config_file and --show_defaults")

    # defaults that can be overwritten by arguments
    tmpl_stored_args = {
        'http_server': 'waitress',
        'lang': 'en',
        'database_engine': 'sqlite',
        'host': '127.0.0.1',
        'port': 5000,
        'error_aggregation_service': None,
    }
    for custom in args.custom:
        # parse arguments
        kwargs = {}
        for el in _escape_split(custom, ','):
            kv = _escape_split(el, '=')
            if len(kv) == 2:
                k, v = kv
                kwargs[k] = v
        # update our template stored args
        tmpl_stored_args.update(kwargs)

    if args.show_defaults:
        for k,v in tmpl_stored_args.iteritems():
            print '%s=%s' % (k, v)
        sys.exit(0)

    # use default that cannot be replaced
    tmpl_stored_args.update({
        'uuid': lambda: uuid.uuid4().hex,
        'here': os.path.dirname(os.path.abspath(args.config_file)),
    })
    try:
        # built in template
        tmpl_file = os.path.join(here, TMPL)

        with open(tmpl_file, 'rb') as f:
            tmpl_data = f.read().decode('utf-8')
            tmpl = Template(tmpl_data).render(**tmpl_stored_args)
        with open(args.config_file, 'wb') as f:
            f.write(tmpl.encode('utf-8'))
        print 'Wrote new config file in %s' % (os.path.abspath(args.config_file))

    except Exception:
        from mako import exceptions
        print exceptions.text_error_template().render()
