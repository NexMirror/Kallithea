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
import datetime
import os
import re
import shutil

import click

import kallithea.bin.kallithea_cli_base as cli_base
from kallithea.lib.utils import REMOVED_REPO_PAT, repo2db_mapper
from kallithea.lib.utils2 import ask_ok, safe_str, safe_unicode
from kallithea.model.db import Repository, Ui
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

@cli_base.register_command(config_file_initialize_app=True)
@click.option('--ask/--no-ask', default=True, help='Ask for confirmation or not. Default is --ask.')
@click.option('--older-than',
        help="""Only purge repositories that have been removed at least the given time ago.
        For example, '--older-than=30d' purges repositories deleted 30 days ago or longer.
        Possible suffixes: d (days), h (hours), m (minutes), s (seconds).""")
def repo_purge_deleted(ask, older_than):
    """Purge backups of deleted repositories.

    When a repository is deleted via the Kallithea web interface, the actual
    data is still present on the filesystem but set aside using a special name.
    This command allows to delete these files permanently.
    """
    def _parse_older_than(val):
        regex = re.compile(r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
        parts = regex.match(val)
        if not parts:
            return
        parts = parts.groupdict()
        time_params = {}
        for (name, param) in parts.iteritems():
            if param:
                time_params[name] = int(param)
        return datetime.timedelta(**time_params)

    def _extract_date(name):
        """
        Extract the date part from rm__<date> pattern of removed repos,
        and convert it to datetime object

        :param name:
        """
        date_part = name[4:19]  # 4:19 since we don't parse milliseconds
        return datetime.datetime.strptime(date_part, '%Y%m%d_%H%M%S')

    repos_location = Ui.get_repos_location()
    to_remove = []
    for dn_, dirs, f in os.walk(safe_str(repos_location)):
        alldirs = list(dirs)
        del dirs[:]
        if ('.hg' in alldirs or
            '.git' in alldirs or
            '.svn' in alldirs or
            'objects' in alldirs and ('refs' in alldirs or 'packed-refs' in f)
        ):
            continue
        for loc in alldirs:
            if REMOVED_REPO_PAT.match(loc):
                to_remove.append([os.path.join(dn_, loc),
                                  _extract_date(loc)])
            else:
                dirs.append(loc)
        if dirs:
            click.echo('Scanning: %s' % dn_)

    if not to_remove:
        click.echo('There are no deleted repositories.')
        return

    # filter older than (if present)!
    if older_than:
        now = datetime.datetime.now()
        to_remove_filtered = []
        older_than_date = _parse_older_than(older_than)
        for name, date_ in to_remove:
            repo_age = now - date_
            if repo_age > older_than_date:
                to_remove_filtered.append([name, date_])

        to_remove = to_remove_filtered

        if not to_remove:
            click.echo('There are no deleted repositories older than %s (%s)'
                    % (older_than, older_than_date))
            return

        click.echo('Considering %s deleted repositories older than %s (%s).'
            % (len(to_remove), older_than, older_than_date))
    else:
        click.echo('Considering %s deleted repositories.' % len(to_remove))

    if not ask:
        remove = True
    else:
        remove = ask_ok('The following repositories will be removed completely:\n%s\n'
                'Do you want to proceed? [y/n] '
                % '\n'.join(['%s deleted on %s' % (safe_str(x[0]), safe_str(x[1]))
                                     for x in to_remove]))

    if remove:
        for path, date_ in to_remove:
            click.echo('Purging repository %s' % path)
            shutil.rmtree(path)
    else:
        click.echo('Nothing done, exiting...')
