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
kallithea.lib.paster_commands.repo_scan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

repo-scan gearbox command for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Feb 9, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import os
import sys

from kallithea.model.scm import ScmModel
from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.lib.utils import repo2db_mapper


class Command(BasePasterCommand):
    """Kallithea: Scan file system for repositories

    Search under the repository root configured in the database,
    all new repositories, and report missing ones with an option of removing them.
    """

    def take_action(self, args):
        rm_obsolete = args.delete_obsolete
        print 'Now scanning root location for new repos ...'
        added, removed = repo2db_mapper(ScmModel().repo_scan(),
                                        remove_obsolete=rm_obsolete)
        added = ', '.join(added) or '-'
        removed = ', '.join(removed) or '-'
        print 'Scan completed.'
        print 'Added: %s' % added
        if rm_obsolete:
            print 'Removed: %s' % removed
        else:
            print 'Missing: %s' % removed

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument(
            '--delete-obsolete',
            action='store_true',
            help="Use this flag do delete repositories that are "
                 "present in Kallithea database but not on the filesystem",
        )

        return parser
