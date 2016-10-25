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
kallithea.lib.paster_commands.ishell
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

interactive shell gearbox command for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 4, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import os
import sys

# imports, used in IPython shell
import time
import shutil
import datetime
from kallithea.model.db import *

from kallithea.lib.paster_commands.common import BasePasterCommand


class Command(BasePasterCommand):
    "Kallithea: Interactive Python shell"

    def take_action(self, args):
        try:
            from IPython import embed
            from IPython.config.loader import Config
            cfg = Config()
            cfg.InteractiveShellEmbed.confirm_exit = False
            embed(config=cfg, banner1="Kallithea IShell.")
        except ImportError:
            print 'Kallithea ishell requires the IPython Python package'
            sys.exit(-1)
