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


@cli_base.register_command(config_file_initialize_app=True)
@click.argument('celery_args', nargs=-1)
def celery_run(celery_args):
    """Start Celery worker(s) for asynchronous tasks.

    This commands starts the Celery daemon which will spawn workers to handle
    certain asynchronous tasks for Kallithea.

    Any extra arguments you pass to this command will be passed through to
    Celery. Use '--' before such extra arguments to avoid options to be parsed
    by this CLI command.
    """

    if not kallithea.CELERY_ON:
        raise Exception('Please set use_celery = true in .ini config '
                        'file before running this command')

    from kallithea.lib import celerypylons
    cmd = celerypylons.worker.worker(celerypylons.app)
    return cmd.run_from_argv(None, command='celery-run -c CONFIG_FILE --', argv=list(celery_args))
