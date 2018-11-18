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
from kallithea.lib.utils2 import safe_unicode
from kallithea.model.db import Repository
from kallithea.model.meta import Session
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

@cli_base.register_command(config_file_initialize_app=True)
@click.argument('repositories', nargs=-1)
def repo_update_metadata(repositories):
    """
    Update repository metadata in database from repository content.

    In normal operation, Kallithea will keep caches up-to-date
    automatically. However, if repositories are externally modified, e.g. by
    a direct push via the filesystem rather than via a Kallithea URL,
    Kallithea is not aware of it. In this case, you should manually run this
    command to update the repository cache.

    If no repositories are specified, the caches of all repositories are
    updated.
    """
    if not repositories:
        repo_list = Repository.query().all()
    else:
        repo_names = [safe_unicode(n.strip()) for n in repositories]
        repo_list = list(Repository.query()
                        .filter(Repository.repo_name.in_(repo_names)))

    for repo in repo_list:
        # update latest revision metadata in database
        repo.update_changeset_cache()
        # invalidate in-memory VCS object cache... will be repopulated on
        # first access
        repo.set_invalidate()

    Session().commit()

    click.echo('Updated database with information about latest change in the following %s repositories:' % (len(repo_list)))
    click.echo('\n'.join(repo.repo_name for repo in repo_list))
