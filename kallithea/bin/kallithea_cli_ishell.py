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
This file was forked by the Kallithea project in July 2014 and later moved.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 4, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import print_function

import sys

import kallithea.bin.kallithea_cli_base as cli_base
from kallithea.model.db import *


@cli_base.register_command(config_file_initialize_app=True)
def ishell():
    """Interactive shell for Kallithea."""
    try:
        from IPython import embed
    except ImportError:
        print('Kallithea ishell requires the Python package IPython 4 or later')
        sys.exit(-1)
    from traitlets.config.loader import Config
    cfg = Config()
    cfg.InteractiveShellEmbed.confirm_exit = False
    embed(config=cfg, banner1="Kallithea IShell.")
