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
import click

import kallithea
import kallithea.bin.kallithea_cli_base as cli_base
from kallithea.lib.db_manage import DbManage
from kallithea.model.meta import Session


@cli_base.register_command(config_file=True)
@click.option('--user', help='Username of administrator account.')
@click.option('--password', help='Password for administrator account.')
@click.option('--email', help='Email address of administrator account.')
@click.option('--repos', help='Absolute path to repositories location.')
@click.option('--force-yes', is_flag=True, help='Answer yes to every question.')
@click.option('--force-no', is_flag=True, help='Answer no to every question.')
@click.option('--public-access/--no-public-access', default=True,
        help='Enable/disable public access on this installation (default: enable)')
def db_create(user, password, email, repos, force_yes, force_no, public_access):
    """Initialize the database.

    Create all required tables in the database specified in the configuration
    file. Create the administrator account. Set certain settings based on
    values you provide.

    You can pass the answers to all questions as options to this command.
    """
    dbconf = kallithea.CONFIG['sqlalchemy.url']

    # force_ask should be True (yes), False (no), or None (ask)
    if force_yes:
        force_ask = True
    elif force_no:
        force_ask = False
    else:
        force_ask = None

    cli_args = dict(
            username=user,
            password=password,
            email=email,
            repos_location=repos,
            force_ask=force_ask,
            public_access=public_access,
    )
    dbmanage = DbManage(dbconf=dbconf, root=kallithea.CONFIG['here'],
                        tests=False, cli_args=cli_args)
    dbmanage.create_tables(override=True)
    repo_root_path = dbmanage.prompt_repo_root_path(None)
    dbmanage.create_settings(repo_root_path)
    dbmanage.create_default_user()
    dbmanage.admin_prompt()
    dbmanage.create_permissions()
    dbmanage.populate_default_permissions()
    Session().commit()

    # initial repository scan
    kallithea.config.middleware.make_app_without_logging(
            kallithea.CONFIG.global_conf, **kallithea.CONFIG.local_conf)
    added, _ = kallithea.lib.utils.repo2db_mapper(kallithea.model.scm.ScmModel().repo_scan())
    if added:
        click.echo('Initial repository scan: added following repositories:')
        click.echo('\t%s' % '\n\t'.join(added))
    else:
        click.echo('Initial repository scan: no repositories found.')

    click.echo('Database set up successfully.')
    click.echo("Don't forget to build the front-end using 'kallithea-cli front-end-build'.")
