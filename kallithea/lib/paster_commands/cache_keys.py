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

cleanup-keys paster command for Kallithea


This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: mar 27, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import with_statement

import os
import sys
import logging

from kallithea.model.meta import Session
from kallithea.lib.utils import BasePasterCommand
from kallithea.model.db import CacheInvalidation

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
    summary = "Cache keys utils"

    def command(self):
        #get SqlAlchemy session
        self._init_session()
        _caches = CacheInvalidation.query().order_by(CacheInvalidation.cache_key).all()
        if self.options.show:
            for c_obj in _caches:
                print 'key:%s active:%s' % (c_obj.cache_key, c_obj.cache_active)
        elif self.options.cleanup:
            for c_obj in _caches:
                Session().delete(c_obj)
                print 'removing key:%s' % (c_obj.cache_key)
                Session().commit()
        else:
            print 'nothing done exiting...'
        sys.exit(0)

    def update_parser(self):
        self.parser.add_option(
            '--show',
            action='store_true',
            dest='show',
            help=("show existing cache keys with together with status")
        )

        self.parser.add_option(
            '--cleanup',
            action="store_true",
            dest="cleanup",
            help="cleanup existing cache keys"
        )
