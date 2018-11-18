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
import functools
import os

import kallithea
import logging.config
import paste.deploy


# This placeholder is the main entry point for the kallithea-cli command
@click.group()
def cli():
    """Various commands to manage a Kallithea instance."""

def register_command(config_file=False, config_file_initialize_app=False):
    """Register a kallithea-cli subcommand.

    If one of the config_file flags are true, a config file must be specified
    with -c and it is read and logging is configured. The configuration is
    available in the kallithea.CONFIG dict.

    If config_file_initialize_app is true, Kallithea, TurboGears global state
    (including tg.config), and database access will also be fully initialized.
    """
    cli_command = cli.command()
    if config_file or config_file_initialize_app:
        def annotator(annotated):
            @click.option('--config_file', '-c', help="Path to .ini file with app configuration.",
                type=click.Path(dir_okay=False, exists=True, readable=True), required=True)
            @functools.wraps(annotated) # reuse meta data from the wrapped function so click can see other options
            def runtime_wrapper(config_file, *args, **kwargs):
                path_to_ini_file = os.path.realpath(config_file)
                kallithea.CONFIG = paste.deploy.appconfig('config:' + path_to_ini_file)
                logging.config.fileConfig(path_to_ini_file)
                if config_file_initialize_app:
                    kallithea.config.middleware.make_app_without_logging(kallithea.CONFIG.global_conf, **kallithea.CONFIG.local_conf)
                    kallithea.lib.utils.setup_cache_regions(kallithea.CONFIG)
                return annotated(*args, **kwargs)
            return cli_command(runtime_wrapper)
        return annotator
    return cli_command
