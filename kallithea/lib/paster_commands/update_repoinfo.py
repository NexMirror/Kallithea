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
kallithea.lib.paster_commands.update_repoinfo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

update-repoinfo gearbox command for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jul 14, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""



from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.lib.utils2 import safe_unicode
from kallithea.model.db import Repository
from kallithea.model.meta import Session


class Command(BasePasterCommand):
    "Kallithea: Update database cache of repository data"

    def take_action(self, args):
        if args.repo_update_list is None:
            repo_list = Repository.query().all()
        else:
            repo_names = [safe_unicode(n.strip())
                          for n in args.repo_update_list.split(',')]
            repo_list = list(Repository.query()
                .filter(Repository.repo_name.in_(repo_names)))
        for repo in repo_list:
            repo.update_changeset_cache()
        Session().commit()

        if args.invalidate_cache:
            for r in repo_list:
                r.set_invalidate()
            print 'Updated repo info and invalidated cache for %s repositories' % (len(repo_list))
        else:
            print 'Updated repo info for %s repositories' % (len(repo_list))

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument('--update-only',
                           action='store',
                           dest='repo_update_list',
                           help="Specifies a comma separated list of repositories "
                                "to update last commit info for. OPTIONAL")
        parser.add_argument('--invalidate-cache',
                           action='store_true',
                           dest='invalidate_cache',
                           help="Trigger cache invalidation event for repos. "
                                "OPTIONAL")

        return parser
