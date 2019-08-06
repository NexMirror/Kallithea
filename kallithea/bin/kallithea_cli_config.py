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

import os
import sys
import uuid
from collections import defaultdict

import click
import mako.exceptions

import kallithea.bin.kallithea_cli_base as cli_base
import kallithea.lib.locale
from kallithea.lib import inifile


def show_defaults(ctx, param, value):
    # Following construct is taken from the Click documentation:
    # https://click.palletsprojects.com/en/7.x/options/#callbacks-and-eager-options
    # "The resilient_parsing flag is applied to the context if Click wants to
    # parse the command line without any destructive behavior that would change
    # the execution flow. In this case, because we would exit the program, we
    # instead do nothing."
    if not value or ctx.resilient_parsing:
        return

    for key, value in inifile.default_variables.items():
        click.echo('%s=%s' % (key, value))

    ctx.exit()

@cli_base.register_command()
@click.option('--show-defaults', callback=show_defaults,
              is_flag=True, expose_value=False, is_eager=True,
              help='Show the default values that can be overridden')
@click.argument('config_file', type=click.Path(dir_okay=False, writable=True), required=True)
@click.argument('key_value_pairs', nargs=-1)
def config_create(config_file, key_value_pairs):
    """Create a new configuration file.

    This command creates a default configuration file, possibly adding/updating
    settings you specify.

    The primary high level configuration keys and their default values are
    shown with --show-defaults . Custom values for these keys can be specified
    on the command line as key=value arguments.

    Additional key=value arguments will be patched/inserted in the [app:main]
    section ... until another section name specifies where any following values
    should go.
    """

    mako_variable_values = {
        'git_hook_interpreter': sys.executable,
        'user_home_path': os.path.expanduser('~'),
        'kallithea_cli_path': cli_base.kallithea_cli_path,
        'ssh_locale': kallithea.lib.locale.get_current_locale(),
    }
    ini_settings = defaultdict(dict)

    section_name = None
    for parameter in key_value_pairs:
        parts = parameter.split('=', 1)
        if len(parts) == 1 and parameter.startswith('[') and parameter.endswith(']'):
            section_name = parameter
        elif len(parts) == 2:
            key, value = parts
            if section_name is None and key in inifile.default_variables:
                mako_variable_values[key] = value
            else:
                if section_name is None:
                    section_name = '[app:main]'
                ini_settings[section_name][key] = value
        else:
            raise ValueError("Invalid name=value parameter %r" % parameter)

    # use default that cannot be replaced
    mako_variable_values.update({
        'uuid': lambda: uuid.uuid4().hex,
    })
    try:
        config_file_abs = os.path.abspath(config_file)
        inifile.create(config_file_abs, mako_variable_values, ini_settings)
        click.echo('Wrote new config file in %s' % config_file_abs)
        click.echo("Don't forget to build the front-end using 'kallithea-cli front-end-build'.")

    except Exception:
        click.echo(mako.exceptions.text_error_template().render())
