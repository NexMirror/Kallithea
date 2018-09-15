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
import kallithea.bin.kallithea_cli_base as cli_base

import os
import subprocess

import kallithea

@cli_base.register_command()
@click.option('--install-deps/--no-install-deps', default=True,
        help='Skip installation of dependencies, via "npm".')
@click.option('--generate/--no-generate', default=True,
        help='Skip generation of front-end files.')
def front_end_build(install_deps, generate):
    """Build the front-end.

    Install required dependencies for the front-end and generate the necessary
    files.  This step is complementary to any 'pip install' step which only
    covers Python dependencies.

    The installation of front-end dependencies happens via the tool 'npm' which
    is expected to be installed already.
    """
    rootdir = os.path.dirname(os.path.dirname(os.path.abspath(kallithea.__file__)))

    if install_deps:
        click.echo("Running 'npm install' to install front-end dependencies from package.json")
        subprocess.check_call(['npm', 'install'], cwd=rootdir)

    if generate:
        click.echo("Generating CSS")
        with open(os.path.join(rootdir, 'kallithea', 'public', 'css', 'pygments.css'), 'w') as f:
            subprocess.check_call(['pygmentize',
                    '-S', 'default',
                    '-f', 'html',
                    '-a', '.code-highlight'],
                    stdout=f)
        lesscpath = os.path.join(rootdir, 'node_modules', '.bin', 'lessc')
        lesspath = os.path.join(rootdir, 'kallithea', 'public', 'less', 'main.less')
        csspath = os.path.join(rootdir, 'kallithea', 'public', 'css', 'style.css')
        subprocess.check_call([lesscpath, '--relative-urls', '--source-map',
                '--source-map-less-inline', lesspath, csspath])
