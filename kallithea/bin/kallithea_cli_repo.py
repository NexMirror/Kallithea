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
:created_on: Feb 9, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""
import click
import kallithea.bin.kallithea_cli_base as cli_base

from kallithea.lib.utils import repo2db_mapper
from kallithea.model.scm import ScmModel

@cli_base.register_command(config_file_initialize_app=True)
@click.option('--remove-missing', is_flag=True,
        help='Remove missing repositories from the Kallithea database.')
def repo_scan(remove_missing):
    """Scan filesystem for repositories.

    Search the configured repository root for new repositories and add them
    into Kallithea.
    Additionally, report repositories that were previously known to Kallithea
    but are no longer present on the filesystem. If option --remove-missing is
    given, remove the missing repositories from the Kallithea database.
    """
    click.echo('Now scanning root location for new repos ...')
    added, removed = repo2db_mapper(ScmModel().repo_scan(),
                                    remove_obsolete=remove_missing)
    click.echo('Scan completed.')
    if added:
        click.echo('Added: %s' % ', '.join(added))
    if removed:
        click.echo('%s: %s' % ('Removed' if remove_missing else 'Missing',
                          ', '.join(removed)))
