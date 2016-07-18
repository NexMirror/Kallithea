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

# Alembic migration environment (configuration).

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool


# The alembic.config.Config object, which wraps the current .ini file.
config = context.config

# Default to use the main Kallithea database string in [app:main].
# For advanced uses, this can be overridden by specifying an explicit
# [alembic] sqlalchemy.url.
database_url = (
    config.get_main_option('sqlalchemy.url') or
    config.get_section_option('app:main', 'sqlalchemy.db1.url')
)

# Configure default logging for Alembic. (This can be overriden by the
# config file, but usually isn't.)
logging.getLogger('alembic').setLevel(logging.WARNING)

# Setup Python loggers based on the config file provided to the alembic
# command.
fileConfig(config.config_file_name, disable_existing_loggers=False)


def run_migrations_offline():
    """Run migrations in 'offline' (--sql) mode.

    This produces an SQL script instead of directly applying the changes.
    Some migrations may not run in offline mode.
    """
    context.configure(
        url=database_url,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    Connects to the database and directly applies the necessary
    migrations.
    """
    cfg = config.get_section(config.config_ini_section)
    cfg['sqlalchemy.url'] = database_url
    connectable = engine_from_config(
        cfg,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
