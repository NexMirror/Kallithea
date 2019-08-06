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

# import commands (they will add themselves to the 'cli' object)
import kallithea.bin.kallithea_cli_celery
import kallithea.bin.kallithea_cli_config
import kallithea.bin.kallithea_cli_db
import kallithea.bin.kallithea_cli_extensions
import kallithea.bin.kallithea_cli_front_end
import kallithea.bin.kallithea_cli_iis
import kallithea.bin.kallithea_cli_index
import kallithea.bin.kallithea_cli_ishell
import kallithea.bin.kallithea_cli_repo
import kallithea.bin.kallithea_cli_ssh
# 'cli' is the main entry point for 'kallithea-cli', specified in setup.py as entry_points console_scripts
from kallithea.bin.kallithea_cli_base import cli
