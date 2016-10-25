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
kallithea.lib.paster_commands.cleanup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

cleanup-repos gearbox command for Kallithea


This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jul 14, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import os
import sys
import re
import shutil
import datetime

from kallithea.lib.paster_commands.common import ask_ok, BasePasterCommand
from kallithea.lib.utils import REMOVED_REPO_PAT
from kallithea.lib.utils2 import safe_str
from kallithea.model.db import Ui


class Command(BasePasterCommand):
    """Kallithea: Cleanup of backup files of deleted repositories"""

    def _parse_older_than(self, val):
        regex = re.compile(r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
        parts = regex.match(val)
        if not parts:
            return
        parts = parts.groupdict()
        time_params = {}
        for (name, param) in parts.iteritems():
            if param:
                time_params[name] = int(param)
        return datetime.timedelta(**time_params)

    def _extract_date(self, name):
        """
        Extract the date part from rm__<date> pattern of removed repos,
        and convert it to datetime object

        :param name:
        """
        date_part = name[4:19]  # 4:19 since we don't parse milliseconds
        return datetime.datetime.strptime(date_part, '%Y%m%d_%H%M%S')

    def take_action(self, args):
        repos_location = Ui.get_repos_location()
        to_remove = []
        for dn_, dirs, f in os.walk(safe_str(repos_location)):
            alldirs = list(dirs)
            del dirs[:]
            if ('.hg' in alldirs or
                '.git' in alldirs or
                '.svn' in alldirs or
                'objects' in alldirs and ('refs' in alldirs or 'packed-refs' in f)):
                continue
            for loc in alldirs:
                if REMOVED_REPO_PAT.match(loc):
                    to_remove.append([os.path.join(dn_, loc),
                                      self._extract_date(loc)])
                else:
                    dirs.append(loc)
            if dirs:
                print 'Scanning: %s' % dn_

        #filter older than (if present)!
        now = datetime.datetime.now()
        older_than = args.older_than
        if older_than:
            to_remove_filtered = []
            older_than_date = self._parse_older_than(older_than)
            for name, date_ in to_remove:
                repo_age = now - date_
                if repo_age > older_than_date:
                    to_remove_filtered.append([name, date_])

            to_remove = to_remove_filtered
            print 'Removing %s deleted repos older than %s (%s)' \
                % (len(to_remove), older_than, older_than_date)
        else:
            print 'Removing all %s deleted repos' % len(to_remove)
        if args.dont_ask or not to_remove:
            # don't ask just remove !
            remove = True
        else:
            remove = ask_ok('the following repositories will be deleted completely:\n%s\n'
                            'are you sure you want to remove them [y/n]?'
                            % '\n'.join(['%s removed on %s' % (safe_str(x[0]), safe_str(x[1]))
                                         for x in to_remove]))

        if remove:
            for path, date_ in to_remove:
                print 'Removing repository %s' % path
                shutil.rmtree(path)
        else:
            print 'Nothing done, exiting...'

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument(
            '--older-than',
            action='store',
            dest='older_than',
            help=("only remove repos that have been removed "
                 "at least given time ago. "
                 "The default is to remove all removed repositories. "
                 "Possible suffixes: "
                 "d (days), h (hours), m (minutes), s (seconds). "
                 "For example --older-than=30d deletes repositories "
                 "removed more than 30 days ago.")
            )

        parser.add_argument(
            '--dont-ask',
            action="store_true",
            dest="dont_ask",
            help="remove repositories without asking for confirmation."
        )

        return parser
