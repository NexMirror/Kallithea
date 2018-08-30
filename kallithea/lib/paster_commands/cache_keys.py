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
kallithea.lib.paster_commands.cache_keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

cleanup-keys gearbox command for Kallithea


This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: mar 27, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""



from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.model.meta import Session
from kallithea.lib.utils2 import safe_str
from kallithea.model.db import CacheInvalidation


class Command(BasePasterCommand):
    "Kallithea: Utilities for managing caching of database content"

    def take_action(self, args):
        _caches = CacheInvalidation.query().order_by(CacheInvalidation.cache_key).all()
        if args.show:
            for c_obj in _caches:
                print 'key:%s active:%s' % (safe_str(c_obj.cache_key), c_obj.cache_active)
        elif args.cleanup:
            for c_obj in _caches:
                Session().delete(c_obj)
                print 'Removing key: %s' % (safe_str(c_obj.cache_key))
            Session().commit()
        else:
            print 'Nothing done, exiting...'

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument(
            '--show',
            action='store_true',
            dest='show',
            help="show existing cache keys with together with status",
        )

        parser.add_argument(
            '--cleanup',
            action="store_true",
            dest="cleanup",
            help="cleanup existing cache keys",
        )

        return parser
