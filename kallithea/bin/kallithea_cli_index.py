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
:created_on: Aug 17, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""
import os
import sys

import click

import kallithea
import kallithea.bin.kallithea_cli_base as cli_base
from kallithea.lib.indexers.daemon import WhooshIndexingDaemon
from kallithea.lib.pidlock import DaemonLock, LockHeld
from kallithea.lib.utils import load_rcextensions
from kallithea.model.repo import RepoModel


@cli_base.register_command(config_file_initialize_app=True)
@click.option('--repo-location', help='Base path of repositories to index. Default: all')
@click.option('--index-only', help='Comma-separated list of repositories to build index on. Default: all')
@click.option('--update-only', help='Comma-separated list of repositories to re-build index on. Default: all')
@click.option('-f', '--full', 'full_index', help='Recreate the index from scratch')
def index_create(repo_location, index_only, update_only, full_index):
    """Create or update full text search index"""

    index_location = kallithea.CONFIG['index_dir']
    load_rcextensions(kallithea.CONFIG['here'])

    if not repo_location:
        repo_location = RepoModel().repos_path
    repo_list = [x.strip() for x in index_only.split(',')] \
        if index_only else None
    repo_update_list = [x.strip() for x in update_only.split(',')] \
        if update_only else None

    try:
        l = DaemonLock(os.path.join(index_location, 'make_index.lock'))
        WhooshIndexingDaemon(index_location=index_location,
                             repo_location=repo_location,
                             repo_list=repo_list,
                             repo_update_list=repo_update_list) \
            .run(full_index=full_index)
        l.release()
    except LockHeld:
        sys.exit(1)
