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
kallithea.lib.paster_commands.setup_db
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Databaset setup gearbox command for Kallithea
"""


import os
import sys
import paste.deploy

from kallithea.lib.db_manage import DbManage
from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.model.meta import Session


# This is almost like SetupAppCommand ... but we have to pass options and it is
# thus simpler to drop websetup and reimplement everything
class Command(BasePasterCommand):
    """Kallithea: Configure the database specified in the .ini file

    Setup Kallithea according to its configuration file.  This is
    the second part of a two-phase web application installation
    process (the first phase is prepare-app). The setup process
    consist of things like setting up databases and creating the admin user
    """

    def get_description(self):
        return self.__doc__.splitlines()[0]

    requires_db_session = False # only available after this command has been run

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument('--user',
                          action='store',
                          dest='username',
                          default=None,
                          help='Admin Username')
        parser.add_argument('--email',
                          action='store',
                          dest='email',
                          default=None,
                          help='Admin Email')
        parser.add_argument('--password',
                          action='store',
                          dest='password',
                          default=None,
                          help='Admin password min 6 chars')
        parser.add_argument('--repos',
                          action='store',
                          dest='repos_location',
                          default=None,
                          help='Absolute path to repositories location')
        parser.add_argument('--force-yes',
                           action='store_true',
                           dest='force_ask',
                           default=None,
                           help='Force yes to every question')
        parser.add_argument('--force-no',
                           action='store_false',
                           dest='force_ask',
                           default=None,
                           help='Force no to every question')
        parser.add_argument('--public-access',
                           action='store_true',
                           dest='public_access',
                           default=None,
                           help='Enable public access on this installation (default)')
        parser.add_argument('--no-public-access',
                           action='store_false',
                           dest='public_access',
                           default=None,
                           help='Disable public access on this installation ')

        return parser

    def take_action(self, opts):
        dbconf = self.config['sqlalchemy.url']
        dbmanage = DbManage(dbconf=dbconf, root=self.config['here'],
                            tests=False, cli_args=vars(opts))
        dbmanage.create_tables(override=True)
        opts = dbmanage.config_prompt(None)
        dbmanage.create_settings(opts)
        dbmanage.create_default_user()
        dbmanage.admin_prompt()
        dbmanage.create_permissions()
        dbmanage.populate_default_permissions()
        Session().commit()
