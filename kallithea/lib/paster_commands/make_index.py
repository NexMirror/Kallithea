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
kallithea.lib.paster_commands.make_index
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

make-index gearbox command for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Aug 17, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import os
import sys

from string import strip
from kallithea.model.repo import RepoModel
from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.lib.utils import load_rcextensions


class Command(BasePasterCommand):
    "Kallithea: Create or update full text search index"

    def take_action(self, args):
        index_location = self.config['index_dir']
        load_rcextensions(self.config['here'])

        repo_location = args.repo_location \
            if args.repo_location else RepoModel().repos_path
        repo_list = map(strip, args.repo_list.split(',')) \
            if args.repo_list else None

        repo_update_list = map(strip, args.repo_update_list.split(',')) \
            if args.repo_update_list else None

        #======================================================================
        # WHOOSH DAEMON
        #======================================================================
        from kallithea.lib.pidlock import LockHeld, DaemonLock
        from kallithea.lib.indexers.daemon import WhooshIndexingDaemon
        try:
            l = DaemonLock(os.path.join(index_location, 'make_index.lock'))
            WhooshIndexingDaemon(index_location=index_location,
                                 repo_location=repo_location,
                                 repo_list=repo_list,
                                 repo_update_list=repo_update_list) \
                .run(full_index=args.full_index)
            l.release()
        except LockHeld:
            sys.exit(1)

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument('--repo-location',
                          action='store',
                          dest='repo_location',
                          help="Specifies repositories location to index OPTIONAL",
                          )
        parser.add_argument('--index-only',
                          action='store',
                          dest='repo_list',
                          help="Specifies a comma separated list of repositories "
                                "to build index on. If not given all repositories "
                                "are scanned for indexing. OPTIONAL",
                          )
        parser.add_argument('--update-only',
                          action='store',
                          dest='repo_update_list',
                          help="Specifies a comma separated list of repositories "
                                "to re-build index on. OPTIONAL",
                          )
        parser.add_argument('-f',
                          action='store_true',
                          dest='full_index',
                          help="Specifies that index should be made full i.e"
                                " destroy old and build from scratch",
                          default=False)

        return parser
