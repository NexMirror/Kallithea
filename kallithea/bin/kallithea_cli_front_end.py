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

import json
import os
import shutil
import subprocess

import click

import kallithea
import kallithea.bin.kallithea_cli_base as cli_base


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
    front_end_dir = os.path.abspath(os.path.join(kallithea.__file__, '..', 'front-end'))
    public_dir = os.path.abspath(os.path.join(kallithea.__file__, '..', 'public'))

    if install_deps:
        click.echo("Running 'npm install' to install front-end dependencies from package.json")
        subprocess.check_call(['npm', 'install'], cwd=front_end_dir, shell=kallithea.is_windows)

    if generate:
        tmp_dir = os.path.join(front_end_dir, 'tmp')
        if not os.path.isdir(tmp_dir):
            os.mkdir(tmp_dir)

        click.echo("Building CSS styling based on Bootstrap")
        with open(os.path.join(tmp_dir, 'pygments.css'), 'w') as f:
            subprocess.check_call(['pygmentize',
                    '-S', 'default',
                    '-f', 'html',
                    '-a', '.code-highlight'],
                    stdout=f)
        lesscpath = os.path.join(front_end_dir, 'node_modules', '.bin', 'lessc')
        lesspath = os.path.join(front_end_dir, 'main.less')
        csspath = os.path.join(public_dir, 'css', 'style.css')
        subprocess.check_call([lesscpath, '--source-map',
                '--source-map-less-inline', lesspath, csspath],
                cwd=front_end_dir, shell=kallithea.is_windows)

        click.echo("Preparing Bootstrap JS")
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'bootstrap', 'dist', 'js', 'bootstrap.js'), os.path.join(public_dir, 'js', 'bootstrap.js'))

        click.echo("Preparing jQuery JS with Flot, Caret and Atwho")
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'jquery', 'dist', 'jquery.min.js'), os.path.join(public_dir, 'js', 'jquery.min.js'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'jquery.flot', 'jquery.flot.js'), os.path.join(public_dir, 'js', 'jquery.flot.js'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'jquery.flot', 'jquery.flot.selection.js'), os.path.join(public_dir, 'js', 'jquery.flot.selection.js'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'jquery.flot', 'jquery.flot.time.js'), os.path.join(public_dir, 'js', 'jquery.flot.time.js'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'jquery.caret', 'dist', 'jquery.caret.min.js'), os.path.join(public_dir, 'js', 'jquery.caret.min.js'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'at.js', 'dist', 'js', 'jquery.atwho.min.js'), os.path.join(public_dir, 'js', 'jquery.atwho.min.js'))

        click.echo("Preparing DataTables JS")
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'datatables.net', 'js', 'jquery.dataTables.js'), os.path.join(public_dir, 'js', 'jquery.dataTables.js'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'datatables.net-bs', 'js', 'dataTables.bootstrap.js'), os.path.join(public_dir, 'js', 'dataTables.bootstrap.js'))

        click.echo("Preparing Select2 JS")
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'select2', 'select2.js'), os.path.join(public_dir, 'js', 'select2.js'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'select2', 'select2.png'), os.path.join(public_dir, 'css', 'select2.png'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'select2', 'select2x2.png'), os.path.join(public_dir, 'css', 'select2x2.png'))
        shutil.copy(os.path.join(front_end_dir, 'node_modules', 'select2', 'select2-spinner.gif'), os.path.join(public_dir, 'css', 'select2-spinner.gif'))

        click.echo("Preparing CodeMirror JS")
        if os.path.isdir(os.path.join(public_dir, 'codemirror')):
            shutil.rmtree(os.path.join(public_dir, 'codemirror'))
        shutil.copytree(os.path.join(front_end_dir, 'node_modules', 'codemirror'), os.path.join(public_dir, 'codemirror'))

        click.echo("Generating LICENSES.txt")
        license_checker_path = os.path.join(front_end_dir, 'node_modules', '.bin', 'license-checker')
        check_licensing_json_path = os.path.join(tmp_dir, 'licensing.json')
        licensing_txt_path = os.path.join(public_dir, 'LICENSES.txt')
        subprocess.check_call([license_checker_path, '--json', '--out', check_licensing_json_path],
                cwd=front_end_dir, shell=kallithea.is_windows)
        with open(check_licensing_json_path) as jsonfile:
            rows = json.loads(jsonfile.read())
            with open(licensing_txt_path, 'w') as out:
                out.write("The Kallithea front-end was built using the following Node modules:\n\n")
                for name_version, values in sorted(rows.items()):
                    name, version = name_version.rsplit('@', 1)
                    line = "%s from https://www.npmjs.com/package/%s/v/%s\n  License: %s\n  Repository: %s\n" % (
                        name_version, name, version, values['licenses'], values.get('repository', '-'))
                    if values.get('copyright'):
                        line += "  Copyright: %s\n" % (values['copyright'])
                    out.write(line + '\n')
